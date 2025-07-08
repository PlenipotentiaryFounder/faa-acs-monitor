#!/usr/bin/env python3
"""
FAA ACS PDF Processor (2024-2025)
Processes downloaded ACS PDFs and extracts structured text using modern techniques.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import re

# PDF Processing libraries (2024-2025 best practices)
try:
    import pymupdf4llm  # AI-optimized extraction
    HAS_PYMUPDF4LLM = True
except ImportError:
    HAS_PYMUPDF4LLM = False

try:
    from pdftext.extraction import plain_text_output, dictionary_output
    HAS_PDFTEXT = True
except ImportError:
    HAS_PDFTEXT = False

try:
    import fitz  # PyMuPDF fallback
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ProcessedDocument:
    """Represents a processed ACS document with extracted content"""
    name: str
    source_path: str
    text_content: str
    structured_content: Optional[Dict] = None
    sections: Optional[List[Dict]] = None
    metadata: Optional[Dict] = None
    processing_method: Optional[str] = None
    processed_at: Optional[str] = None

class ACSProcessor:
    """Modern PDF processor for ACS documents"""
    
    def __init__(self):
        self.data_dir = Path("data")
        self.docs_dir = self.data_dir / "acs-documents"
        self.text_dir = self.data_dir / "extracted-text"
        self.metadata_dir = self.data_dir / "metadata"
        
        # Create directories
        for dir_path in [self.text_dir, self.metadata_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Determine best processing method
        self.processing_method = self._determine_processing_method()
        logger.info(f"Using processing method: {self.processing_method}")
    
    def _determine_processing_method(self) -> str:
        """Determine the best available PDF processing method"""
        if HAS_PYMUPDF4LLM:
            return "pymupdf4llm"
        elif HAS_PDFTEXT:
            return "pdftext"
        elif HAS_PYMUPDF:
            return "pymupdf"
        else:
            raise ImportError("No PDF processing library available. Install pymupdf4llm, pdftext, or PyMuPDF")
    
    def extract_text_pymupdf4llm(self, pdf_path: Path) -> tuple[str, Dict]:
        """Extract text using PyMuPDF4LLM (2024-2025 best practice)"""
        try:
            # AI-optimized markdown extraction
            markdown_text = pymupdf4llm.to_markdown(str(pdf_path))
            
            # Extract metadata
            doc = fitz.open(pdf_path) if HAS_PYMUPDF else None
            metadata = {}
            if doc:
                metadata = {
                    'page_count': doc.page_count,
                    'title': doc.metadata.get('title', ''),
                    'author': doc.metadata.get('author', ''),
                    'creation_date': doc.metadata.get('creationDate', ''),
                    'modification_date': doc.metadata.get('modDate', '')
                }
                doc.close()
            
            return markdown_text, metadata
            
        except Exception as e:
            logger.error(f"PyMuPDF4LLM extraction failed: {e}")
            return "", {}
    
    def extract_text_pdftext(self, pdf_path: Path) -> tuple[str, Dict]:
        """Extract text using PDFText"""
        try:
            # Plain text extraction
            text = plain_text_output(str(pdf_path), sort=True, hyphens=False)
            
            # Structured data extraction
            structured = dictionary_output(str(pdf_path), sort=True)
            
            metadata = {
                'page_count': len(structured) if structured else 0,
                'extraction_method': 'pdftext'
            }
            
            return text, metadata
            
        except Exception as e:
            logger.error(f"PDFText extraction failed: {e}")
            return "", {}
    
    def extract_text_pymupdf(self, pdf_path: Path) -> tuple[str, Dict]:
        """Extract text using PyMuPDF (fallback)"""
        try:
            doc = fitz.open(pdf_path)
            
            text_content = []
            for page in doc:
                text_content.append(page.get_text())
            
            full_text = "\n".join(text_content)
            
            metadata = {
                'page_count': doc.page_count,
                'title': doc.metadata.get('title', ''),
                'author': doc.metadata.get('author', ''),
                'creation_date': doc.metadata.get('creationDate', ''),
                'modification_date': doc.metadata.get('modDate', '')
            }
            
            doc.close()
            return full_text, metadata
            
        except Exception as e:
            logger.error(f"PyMuPDF extraction failed: {e}")
            return "", {}
    
    def extract_text(self, pdf_path: Path) -> tuple[str, Dict]:
        """Extract text using the best available method"""
        if self.processing_method == "pymupdf4llm":
            return self.extract_text_pymupdf4llm(pdf_path)
        elif self.processing_method == "pdftext":
            return self.extract_text_pdftext(pdf_path)
        elif self.processing_method == "pymupdf":
            return self.extract_text_pymupdf(pdf_path)
        else:
            return "", {}
    
    def parse_acs_sections(self, text: str) -> List[Dict]:
        """Parse ACS document sections using pattern matching"""
        sections = []
        
        # Common ACS section patterns
        section_patterns = [
            r'(AREA OF OPERATION\s+[IVXLC]+)\s*[:\-]\s*([^\n]+)',
            r'(TASK\s+[A-Z]+)\.\s*([^\n]+)',
            r'(REFERENCES?:?\s*)([^\n]+)',
            r'(OBJECTIVE:?\s*)([^\n]+)',
            r'(KNOWLEDGE:?\s*)([^\n]+)',
            r'(RISK MANAGEMENT:?\s*)([^\n]+)',
            r'(SKILLS:?\s*)([^\n]+)'
        ]
        
        current_position = 0
        
        for pattern in section_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                section_type = match.group(1).strip()
                content = match.group(2).strip()
                
                sections.append({
                    'type': section_type,
                    'content': content,
                    'position': match.start(),
                    'length': len(match.group(0))
                })
        
        # Sort by position in document
        sections.sort(key=lambda x: x['position'])
        return sections
    
    def extract_acs_standards(self, text: str) -> Dict[str, List[str]]:
        """Extract specific ACS standards and requirements"""
        standards = {
            'areas_of_operation': [],
            'tasks': [],
            'references': [],
            'objectives': [],
            'knowledge_elements': [],
            'risk_management': [],
            'skill_elements': []
        }
        
        # Extract Areas of Operation
        aoo_pattern = r'AREA OF OPERATION\s+([IVXLC]+)\s*[:\-]\s*([^\n]+)'
        for match in re.finditer(aoo_pattern, text, re.IGNORECASE):
            standards['areas_of_operation'].append({
                'number': match.group(1),
                'title': match.group(2).strip()
            })
        
        # Extract Tasks
        task_pattern = r'TASK\s+([A-Z]+)\.\s*([^\n]+)'
        for match in re.finditer(task_pattern, text, re.IGNORECASE):
            standards['tasks'].append({
                'code': match.group(1),
                'title': match.group(2).strip()
            })
        
        # Extract references (common pattern in ACS documents)
        ref_patterns = [
            r'14 CFR part (\d+)',
            r'AC (\d+-\d+[A-Z]*)',
            r'AIM (\d+-\d+-\d+)',
            r'POH/AFM'
        ]
        
        for pattern in ref_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                standards['references'].append(match.group(0))
        
        return standards
    
    def process_document(self, pdf_path: Path) -> ProcessedDocument:
        """Process a single ACS document"""
        logger.info(f"Processing {pdf_path.name}...")
        
        # Extract text
        text_content, metadata = self.extract_text(pdf_path)
        
        if not text_content:
            logger.warning(f"No text extracted from {pdf_path.name}")
            return ProcessedDocument(
                name=pdf_path.stem,
                source_path=str(pdf_path),
                text_content="",
                processing_method=self.processing_method,
                processed_at=datetime.now().isoformat()
            )
        
        # Parse sections
        sections = self.parse_acs_sections(text_content)
        
        # Extract ACS standards
        acs_standards = self.extract_acs_standards(text_content)
        
        # Create structured content
        structured_content = {
            'standards': acs_standards,
            'metadata': metadata,
            'word_count': len(text_content.split()),
            'character_count': len(text_content)
        }
        
        return ProcessedDocument(
            name=pdf_path.stem,
            source_path=str(pdf_path),
            text_content=text_content,
            structured_content=structured_content,
            sections=sections,
            metadata=metadata,
            processing_method=self.processing_method,
            processed_at=datetime.now().isoformat()
        )
    
    def save_processed_document(self, doc: ProcessedDocument):
        """Save processed document data"""
        # Save plain text
        text_file = self.text_dir / f"{doc.name}.txt"
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(doc.text_content)
        
        # Save structured data as markdown
        md_file = self.text_dir / f"{doc.name}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(f"# {doc.name}\n\n")
            f.write(f"**Processed:** {doc.processed_at}  \n")
            f.write(f"**Method:** {doc.processing_method}  \n")
            f.write(f"**Source:** {doc.source_path}  \n\n")
            
            if doc.structured_content and doc.structured_content.get('standards'):
                standards = doc.structured_content['standards']
                
                if standards['areas_of_operation']:
                    f.write("## Areas of Operation\n\n")
                    for aoo in standards['areas_of_operation']:
                        f.write(f"- **{aoo['number']}**: {aoo['title']}\n")
                    f.write("\n")
                
                if standards['tasks']:
                    f.write("## Tasks\n\n")
                    for task in standards['tasks']:
                        f.write(f"- **{task['code']}**: {task['title']}\n")
                    f.write("\n")
                
                if standards['references']:
                    f.write("## References\n\n")
                    for ref in set(standards['references']):  # Remove duplicates
                        f.write(f"- {ref}\n")
                    f.write("\n")
            
            f.write("## Full Text\n\n")
            f.write(doc.text_content)
        
        # Save metadata as JSON
        metadata_file = self.metadata_dir / f"{doc.name}_processed.json"
        with open(metadata_file, 'w') as f:
            json.dump(asdict(doc), f, indent=2, default=str)
    
    def process_all_documents(self):
        """Process all downloaded ACS documents"""
        if not self.docs_dir.exists():
            logger.warning("No documents directory found")
            return
        
        pdf_files = list(self.docs_dir.glob("*.pdf"))
        
        if not pdf_files:
            logger.info("No PDF files found to process")
            return
        
        logger.info(f"Processing {len(pdf_files)} documents...")
        
        processed_docs = []
        
        for pdf_file in pdf_files:
            try:
                processed_doc = self.process_document(pdf_file)
                self.save_processed_document(processed_doc)
                processed_docs.append(processed_doc)
                logger.info(f"✅ Processed {pdf_file.name}")
                
            except Exception as e:
                logger.error(f"❌ Failed to process {pdf_file.name}: {e}")
        
        # Create processing summary
        summary = {
            'processed_at': datetime.now().isoformat(),
            'total_documents': len(pdf_files),
            'successfully_processed': len(processed_docs),
            'processing_method': self.processing_method,
            'documents': [doc.name for doc in processed_docs]
        }
        
        summary_file = self.metadata_dir / "processing_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Processing complete: {len(processed_docs)}/{len(pdf_files)} documents")

def main():
    """Main entry point"""
    processor = ACSProcessor()
    processor.process_all_documents()

if __name__ == "__main__":
    main()