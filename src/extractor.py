import os
import sys
import subprocess
import platform
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==========================================
# 1. DEPENDENCIES & SETUP
# ==========================================

# --- PDF Dependencies ---
try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    logger.warning("PyPDF2 not found. Install with: pip install PyPDF2")

try:
    import pytesseract
    from pdf2image import convert_from_path
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("OCR libraries not found. Install with: pip install pytesseract pdf2image")

# --- Word Dependencies ---
try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    logger.warning("python-docx not found. Install with: pip install python-docx")

# --- Tika Dependencies ---
try:
    import tika
    from tika import parser
    TIKA_AVAILABLE = True
    logger.info("Tika is available")
except ImportError:
    TIKA_AVAILABLE = False
    logger.warning("Tika not available. Install with: pip install tika")

# ==========================================
# 2. COMMON UTILITIES
# ==========================================

def extract_resume_sections(text: str) -> Dict[str, str]:
    """
    Extract structured sections from resume text.
    """
    sections = {
        "contact_info": "",
        "skills": "",
        "experience": "",
        "education": "",
        "summary": "",
        "other": ""
    }
    
    # Simple section extraction using keywords
    lines = text.split('\n')
    current_section = "other"
    
    for line in lines:
        line_lower = line.lower().strip()
        
        # Detect sections based on keywords
        if any(keyword in line_lower for keyword in ['skill', 'technology', 'programming', 'framework']):
            current_section = "skills"
        elif any(keyword in line_lower for keyword in ['experience', 'work', 'employment', 'job']):
            current_section = "experience"
        elif any(keyword in line_lower for keyword in ['education', 'degree', 'university', 'college', 'school']):
            current_section = "education"
        elif any(keyword in line_lower for keyword in ['summary', 'profile', 'objective', 'about']):
            current_section = "summary"
        elif any(keyword in line_lower for keyword in ['email', 'phone', '@', 'linkedin', 'github']):
            current_section = "contact_info"
        
        # Add line to current section
        if line.strip():
            sections[current_section] += line + "\n"
    
    # Clean up sections
    for key in sections:
        sections[key] = sections[key].strip()
    
    return sections

class JavaChecker:
    """Check and install Java for Tika."""
    
    @staticmethod
    def check_java_installed() -> bool:
        """Check if Java is installed and accessible."""
        try:
            result = subprocess.run(['java', '-version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info("Java is already installed")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        logger.warning("Java not found or not accessible")
        return False
    
    @staticmethod
    def install_java() -> bool:
        """Install Java based on the operating system."""
        system = platform.system().lower()
        
        try:
            if system == "darwin":  # macOS
                logger.info("Installing Java on macOS...")
                result = subprocess.run(['brew', 'install', 'openjdk@11'], 
                                      capture_output=True, text=True, timeout=300)
                if result.returncode == 0:
                    # Create symlink for system-wide access
                    subprocess.run(['sudo', 'ln', '-sfn', 
                                  '/opt/homebrew/opt/openjdk@11/libexec/openjdk.jdk', 
                                  '/Library/Java/JavaVirtualMachines/openjdk-11.jdk'])
                    logger.info("Java installed successfully on macOS")
                    return True
                else:
                    logger.error(f"Failed to install Java: {result.stderr}")
                    return False
                    
            elif system == "linux":
                logger.info("Installing Java on Linux...")
                # Try different package managers
                package_managers = [
                    ['sudo', 'apt-get', 'update', '&&', 'sudo', 'apt-get', 'install', '-y', 'openjdk-11-jdk'],
                    ['sudo', 'yum', 'install', '-y', 'java-11-openjdk'],
                    ['sudo', 'dnf', 'install', '-y', 'java-11-openjdk']
                ]
                
                for cmd in package_managers:
                    try:
                        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
                        if result.returncode == 0:
                            logger.info("Java installed successfully on Linux")
                            return True
                    except subprocess.TimeoutExpired:
                        continue
                
                logger.error("Failed to install Java on Linux")
                return False
                
            elif system == "windows":
                logger.info("Please install Java manually on Windows:")
                logger.info("Download from: https://adoptium.net/")
                return False
                
            else:
                logger.error(f"Unsupported operating system: {system}")
                return False
                
        except Exception as e:
            logger.error(f"Error installing Java: {e}")
            return False
    
    @staticmethod
    def ensure_java_available() -> bool:
        """Ensure Java is available, install if needed."""
        if JavaChecker.check_java_installed():
            return True
        
        logger.info("Java not found. Attempting to install...")
        return JavaChecker.install_java()

# ==========================================
# 3. PDF EXTRACTOR
# ==========================================

class PDFExtractor:
    """Advanced PDF text extractor with OCR support and error handling."""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self.reader = None
        self.is_encrypted = False
        self.text_content = {}
        
    def validate_file(self) -> bool:
        """Validate PDF file exists and is accessible."""
        if not self.pdf_path.exists():
            logger.error(f"PDF file not found: {self.pdf_path}")
            return False
        
        if not self.pdf_path.is_file():
            logger.error(f"Path is not a file: {self.pdf_path}")
            return False
            
        if self.pdf_path.stat().st_size == 0:
            logger.error(f"PDF file is empty: {self.pdf_path}")
            return False
            
        return True
    
    def load_pdf(self) -> bool:
        """Load PDF with error handling."""
        try:
            self.reader = PdfReader(self.pdf_path)
            
            # Check if PDF is encrypted
            if self.reader.is_encrypted:
                self.is_encrypted = True
                logger.warning("PDF is encrypted. Text extraction may be limited.")
                
            logger.info(f"PDF loaded successfully. Pages: {len(self.reader.pages)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load PDF: {e}")
            return False
    
    def extract_text_from_page(self, page, page_num: int) -> str:
        """Extract text from a single page using multiple methods."""
        text = ""
        
        # Method 1: Direct text extraction
        try:
            text = page.extract_text()
            if text and text.strip():
                logger.info(f"Page {page_num + 1}: Text extracted successfully")
                return text
        except Exception as e:
            logger.warning(f"Page {page_num + 1}: Text extraction failed - {e}")
        
        # Method 2: OCR for scanned PDFs (if available)
        if not text and OCR_AVAILABLE:
            try:
                text = self._extract_text_with_ocr(page_num)
                if text and text.strip():
                    logger.info(f"Page {page_num + 1}: Text extracted via OCR")
                    return text
            except Exception as e:
                logger.warning(f"Page {page_num + 1}: OCR failed - {e}")
        
        # Method 3: Try alternative extraction methods
        try:
            # Try to get text from annotations
            if hasattr(page, 'annotations'):
                for annotation in page.annotations:
                    if hasattr(annotation, 'get_text'):
                        text += annotation.get_text() + "\n"
            
            # Try to get text from form fields
            if hasattr(page, 'get_form_text_fields'):
                form_fields = page.get_form_text_fields()
                for field_name, field_value in form_fields.items():
                    if field_value:
                        text += f"{field_name}: {field_value}\n"
                        
        except Exception as e:
            logger.debug(f"Alternative extraction methods failed: {e}")
        
        return text.strip() if text else ""
    
    def _extract_text_with_ocr(self, page_num: int) -> str:
        """Extract text from scanned PDF using OCR."""
        try:
            # Convert PDF page to image
            images = convert_from_path(
                self.pdf_path, 
                first_page=page_num + 1, 
                last_page=page_num + 1,
                dpi=300  # Higher DPI for better OCR accuracy
            )
            
            if images:
                # Extract text using OCR
                text = pytesseract.image_to_string(images[0], lang='eng')
                return text
                
        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
            
        return ""
    
    def extract_all_text(self) -> Dict[str, Any]:
        """Extract text from all pages with comprehensive metadata."""
        if not self.validate_file():
            return {"error": "Invalid PDF file"}
        
        if not self.load_pdf():
            return {"error": "Failed to load PDF"}
        
        result = {
            "file_path": str(self.pdf_path),
            "total_pages": len(self.reader.pages),
            "is_encrypted": self.is_encrypted,
            "pages": {},
            "full_text": "",
            "metadata": {}
        }
        
        # Extract metadata
        try:
            if self.reader.metadata:
                result["metadata"] = {
                    "title": self.reader.metadata.get('/Title', ''),
                    "author": self.reader.metadata.get('/Author', ''),
                    "subject": self.reader.metadata.get('/Subject', ''),
                    "creator": self.reader.metadata.get('/Creator', ''),
                    "producer": self.reader.metadata.get('/Producer', ''),
                    "creation_date": self.reader.metadata.get('/CreationDate', ''),
                    "modification_date": self.reader.metadata.get('/ModDate', '')
                }
        except Exception as e:
            logger.warning(f"Failed to extract metadata: {e}")
        
        # Extract text from each page
        for page_num, page in enumerate(self.reader.pages):
            page_text = self.extract_text_from_page(page, page_num)
            
            result["pages"][page_num + 1] = {
                "text": page_text,
                "has_text": bool(page_text.strip()),
                "extraction_method": "direct" if page_text else "none"
            }
            
            result["full_text"] += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
        
        return result
    
    def save_extracted_text(self, output_path: Optional[str] = None) -> str:
        """Save extracted text to a file."""
        result = self.extract_all_text()
        
        if "error" in result:
            logger.error(f"Cannot save: {result['error']}")
            return ""
        
        if not output_path:
            output_path = self.pdf_path.with_suffix('.txt')
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"PDF Text Extraction Results\n")
                f.write(f"File: {result['file_path']}\n")
                f.write(f"Pages: {result['total_pages']}\n")
                f.write(f"Encrypted: {result['is_encrypted']}\n")
                f.write(f"Extracted on: {result.get('extraction_date', 'Unknown')}\n")
                f.write("=" * 50 + "\n\n")
                f.write(result['full_text'])
            
            logger.info(f"Text saved to: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Failed to save text: {e}")
            return ""

def extract_pdf_text(file_path: str) -> Dict[str, Any]:
    """
    Extract text from a single PDF file.
    """
    try:
        extractor = PDFExtractor(file_path)
        result = extractor.extract_all_text()
        
        if "error" in result:
            return {
                "success": False,
                "file_path": file_path,
                "error": result["error"]
            }
        
        return {
            "success": True,
            "file_path": file_path,
            "text": result["full_text"],
            "metadata": result["metadata"],
            "pages": result["pages"],
            "total_pages": result["total_pages"],
            "is_encrypted": result["is_encrypted"]
        }
        
    except Exception as e:
        logger.error(f"Failed to extract text from {file_path}: {e}")
        return {
            "success": False,
            "file_path": file_path,
            "error": str(e)
        }

# ==========================================
# 4. WORD EXTRACTOR
# ==========================================

class WordExtractor:
    """Advanced Word document text extractor with error handling."""
    
    def __init__(self, docx_path: str):
        self.docx_path = Path(docx_path)
        self.document = None
        self.text_content = {}
        
    def validate_file(self) -> bool:
        """Validate Word document file exists and is accessible."""
        if not self.docx_path.exists():
            logger.error(f"Word document not found: {self.docx_path}")
            return False
        
        if not self.docx_path.is_file():
            logger.error(f"Path is not a file: {self.docx_path}")
            return False
            
        if self.docx_path.stat().st_size == 0:
            logger.error(f"Word document is empty: {self.docx_path}")
            return False
            
        # Check if it's a .docx file
        if self.docx_path.suffix.lower() not in ['.docx', '.doc']:
            logger.warning(f"File may not be a Word document: {self.docx_path}")
            
        return True
    
    def load_document(self) -> bool:
        """Load Word document with error handling."""
        try:
            self.document = Document(self.docx_path)
            logger.info(f"Word document loaded successfully. Paragraphs: {len(self.document.paragraphs)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load Word document: {e}")
            return False
    
    def extract_text_from_paragraphs(self) -> str:
        """Extract text from all paragraphs."""
        text = ""
        
        try:
            for paragraph in self.document.paragraphs:
                if paragraph.text.strip():
                    text += paragraph.text + "\n"
                    
            logger.info(f"Extracted text from {len(self.document.paragraphs)} paragraphs")
            return text.strip()
            
        except Exception as e:
            logger.error(f"Failed to extract text from paragraphs: {e}")
            return ""
    
    def extract_text_from_tables(self) -> str:
        """Extract text from all tables."""
        text = ""
        
        try:
            for table in self.document.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        if cell.text.strip():
                            row_text.append(cell.text.strip())
                    if row_text:
                        text += " | ".join(row_text) + "\n"
                text += "\n"  # Add space between tables
                
            logger.info(f"Extracted text from {len(self.document.tables)} tables")
            return text.strip()
            
        except Exception as e:
            logger.error(f"Failed to extract text from tables: {e}")
            return ""
    
    def extract_document_properties(self) -> Dict[str, str]:
        """Extract document properties/metadata."""
        properties = {
            "title": "",
            "author": "",
            "subject": "",
            "keywords": "",
            "comments": "",
            "category": "",
            "created": "",
            "modified": ""
        }
        
        try:
            core_props = self.document.core_properties
            
            if core_props.title:
                properties["title"] = core_props.title
            if core_props.author:
                properties["author"] = core_props.author
            if core_props.subject:
                properties["subject"] = core_props.subject
            if core_props.keywords:
                properties["keywords"] = core_props.keywords
            if core_props.comments:
                properties["comments"] = core_props.comments
            if core_props.category:
                properties["category"] = core_props.category
            if core_props.created:
                properties["created"] = str(core_props.created)
            if core_props.modified:
                properties["modified"] = str(core_props.modified)
                
        except Exception as e:
            logger.warning(f"Failed to extract document properties: {e}")
            
        return properties
    
    def extract_all_text(self) -> Dict[str, Any]:
        """Extract all text from Word document with comprehensive metadata."""
        if not self.validate_file():
            return {"error": "Invalid Word document file"}
        
        if not self.load_document():
            return {"error": "Failed to load Word document"}
        
        # Extract text from different sources
        paragraph_text = self.extract_text_from_paragraphs()
        table_text = self.extract_text_from_tables()
        
        # Combine all text
        full_text = ""
        if paragraph_text:
            full_text += paragraph_text + "\n\n"
        if table_text:
            full_text += "--- TABLES ---\n" + table_text + "\n\n"
        
        full_text = full_text.strip()
        
        result = {
            "file_path": str(self.docx_path),
            "total_paragraphs": len(self.document.paragraphs),
            "total_tables": len(self.document.tables),
            "paragraphs": {},
            "tables": {},
            "full_text": full_text,
            "metadata": self.extract_document_properties()
        }
        
        # Extract individual paragraphs with formatting info
        for i, paragraph in enumerate(self.document.paragraphs):
            result["paragraphs"][i + 1] = {
                "text": paragraph.text,
                "style": paragraph.style.name if paragraph.style else "Normal",
                "has_text": bool(paragraph.text.strip()),
                "runs": len(paragraph.runs)
            }
        
        # Extract individual tables
        for i, table in enumerate(self.document.tables):
            table_data = []
            for row in table.rows:
                row_data = []
                for cell in row.cells:
                    row_data.append(cell.text.strip())
                table_data.append(row_data)
            
            result["tables"][i + 1] = {
                "rows": len(table.rows),
                "columns": len(table.columns) if table.rows else 0,
                "data": table_data
            }
        
        return result
    
    def save_extracted_text(self, output_path: Optional[str] = None) -> str:
        """Save extracted text to a file."""
        result = self.extract_all_text()
        
        if "error" in result:
            logger.error(f"Cannot save: {result['error']}")
            return ""
        
        if not output_path:
            output_path = self.docx_path.with_suffix('.txt')
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"Word Document Text Extraction Results\n")
                f.write(f"File: {result['file_path']}\n")
                f.write(f"Paragraphs: {result['total_paragraphs']}\n")
                f.write(f"Tables: {result['total_tables']}\n")
                f.write("=" * 50 + "\n\n")
                f.write(result['full_text'])
            
            logger.info(f"Text saved to: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Failed to save text: {e}")
            return ""

def extract_word_text(file_path: str) -> Dict[str, Any]:
    """
    Extract text from a single Word document file.
    """
    try:
        extractor = WordExtractor(file_path)
        result = extractor.extract_all_text()
        
        if "error" in result:
            return {
                "success": False,
                "file_path": file_path,
                "error": result["error"]
            }
        
        return {
            "success": True,
            "file_path": file_path,
            "text": result["full_text"],
            "metadata": result["metadata"],
            "paragraphs": result["paragraphs"],
            "tables": result["tables"],
            "total_paragraphs": result["total_paragraphs"],
            "total_tables": result["total_tables"]
        }
        
    except Exception as e:
        logger.error(f"Failed to extract text from {file_path}: {e}")
        return {
            "success": False,
            "file_path": file_path,
            "error": str(e)
        }

# ==========================================
# 5. UNIVERSAL EXTRACTOR (TIKA FALLBACK)
# ==========================================

class UniversalParser:
    """Universal document parser with fallback to Tika."""
    
    def __init__(self):
        self.java_available = False
        self.tika_available = TIKA_AVAILABLE
        
        # Ensure Java is available if Tika is needed
        if self.tika_available:
            self.java_available = JavaChecker.ensure_java_available()
    
    def extract_with_tika(self, file_path: str) -> Dict[str, Any]:
        """Extract text using Apache Tika."""
        if not self.tika_available:
            return {
                "success": False,
                "file_path": file_path,
                "error": "Tika not available",
                "method": "tika"
            }
        
        if not self.java_available:
            return {
                "success": False,
                "file_path": file_path,
                "error": "Java not available for Tika",
                "method": "tika"
            }
        
        try:
            logger.info(f"Extracting with Tika: {file_path}")
            
            # Parse document with Tika
            raw = parser.from_file(file_path)
            
            if raw and raw.get("content"):
                return {
                    "success": True,
                    "file_path": file_path,
                    "text": raw["content"].strip(),
                    "metadata": raw.get("metadata", {}),
                    "content_type": raw.get("metadata", {}).get("Content-Type", ""),
                    "method": "tika"
                }
            else:
                return {
                    "success": False,
                    "file_path": file_path,
                    "error": "Tika returned no content",
                    "method": "tika"
                }
                
        except Exception as e:
            logger.error(f"Tika extraction failed: {e}")
            return {
                "success": False,
                "file_path": file_path,
                "error": str(e),
                "method": "tika"
            }
    
    def extract_document(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text from document using specialized parsers first,
        then fallback to Tika if needed.
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {
                "success": False,
                "file_path": str(file_path),
                "error": "File not found",
                "method": "none"
            }
        
        # Try specialized parsers first
        if file_path.suffix.lower() == '.pdf' and PYPDF2_AVAILABLE:
            logger.info(f"Trying PDF parser: {file_path}")
            result = extract_pdf_text(str(file_path))
            if result["success"]:
                result["method"] = "pdf_parser"
                return result
            else:
                logger.warning(f"PDF parser failed, trying Tika: {result['error']}")
        
        elif file_path.suffix.lower() in ['.docx', '.doc'] and DOCX_AVAILABLE:
            logger.info(f"Trying Word parser: {file_path}")
            result = extract_word_text(str(file_path))
            if result["success"]:
                result["method"] = "word_parser"
                return result
            else:
                logger.warning(f"Word parser failed, trying Tika: {result['error']}")
        
        # Fallback to Tika for any format
        logger.info(f"Falling back to Tika: {file_path}")
        return self.extract_with_tika(str(file_path))
    
    def process_batch_documents(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Process multiple documents with fallback strategy.
        """
        results = []
        total_files = len(file_paths)
        
        logger.info(f"Starting batch processing of {total_files} files")
        
        for i, file_path in enumerate(file_paths, 1):
            logger.info(f"Processing file {i}/{total_files}: {file_path}")
            result = self.extract_document(file_path)
            results.append(result)
            
            if result["success"]:
                logger.info(f"✓ Successfully processed: {file_path} (method: {result['method']})")
            else:
                logger.warning(f"✗ Failed to process: {file_path} - {result['error']}")
        
        # Summary statistics
        successful = sum(1 for r in results if r["success"])
        failed = total_files - successful
        
        # Method breakdown
        methods = {}
        for r in results:
            method = r.get("method", "unknown")
            methods[method] = methods.get(method, 0) + 1
        
        logger.info(f"Batch processing complete: {successful} successful, {failed} failed")
        logger.info(f"Method breakdown: {methods}")
        
        return results

def extract_any_document(file_path: str) -> Dict[str, Any]:
    """
    Universal document extraction function.
    """
    parser = UniversalParser()
    return parser.extract_document(file_path)

def process_batch_any_documents(file_paths: List[str]) -> List[Dict[str, Any]]:
    """
    Process multiple documents of any format.
    """
    parser = UniversalParser()
    return parser.process_batch_documents(file_paths)

# ==========================================
# 6. MAIN EXECUTION
# ==========================================

def main():
    """Main function for command line usage."""
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        result = extract_any_document(file_path)
        
        if result["success"]:
            print(f"✓ Successfully extracted text from: {file_path}")
            print(f"Method used: {result['method']}")
            print(f"Text length: {len(result['text'])} characters")
            print(f"Content type: {result.get('content_type', 'N/A')}")
        else:
            print(f"✗ Failed to extract text: {result['error']}")
            print(f"Method attempted: {result.get('method', 'N/A')}")
    else:
        print("Usage: python extractor.py <file_path>")
        print("Supports: PDF, Word, PowerPoint, Excel, Text, and many more formats")

if __name__ == "__main__":
    main()
