#!/usr/bin/env python3
"""
FAA ACS Document Monitor (2024-2025)
Monitors FAA ACS documents for changes and downloads updated versions.
"""

import requests
import json
import hashlib
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import logging
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ACSDocument:
    """Represents an ACS document with metadata"""
    name: str
    url: str
    last_modified: Optional[str] = None
    etag: Optional[str] = None
    content_hash: Optional[str] = None
    file_size: Optional[int] = None
    local_path: Optional[str] = None
    last_checked: Optional[str] = None

class FAAMonitor:
    """Main monitor class for FAA ACS documents"""
    
    def __init__(self):
        self.base_url = "https://www.faa.gov"
        self.acs_base = "/training_testing/testing/acs"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Create directories
        self.data_dir = Path("data")
        self.docs_dir = self.data_dir / "acs-documents"
        self.metadata_dir = self.data_dir / "metadata"
        self.logs_dir = Path("logs")
        
        for dir_path in [self.docs_dir, self.metadata_dir, self.logs_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def discover_acs_documents(self) -> List[ACSDocument]:
        """Discover all ACS documents from the FAA website"""
        logger.info("Discovering ACS documents from FAA website...")
        
        documents = []
        acs_url = urljoin(self.base_url, self.acs_base)
        
        try:
            response = self.session.get(acs_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find PDF links (ACS documents are typically PDFs)
            pdf_links = soup.find_all('a', href=lambda x: x and x.endswith('.pdf'))
            
            for link in pdf_links:
                href = link.get('href')
                if href:
                    # Convert relative URLs to absolute
                    if not href.startswith('http'):
                        href = urljoin(self.base_url, href)
                    
                    # Extract document name
                    doc_name = link.get_text(strip=True) or Path(urlparse(href).path).stem
                    
                    # Filter for ACS documents (contain keywords)
                    acs_keywords = ['acs', 'airman', 'certification', 'standards']
                    if any(keyword in doc_name.lower() or keyword in href.lower() 
                          for keyword in acs_keywords):
                        
                        documents.append(ACSDocument(
                            name=doc_name,
                            url=href,
                            last_checked=datetime.now().isoformat()
                        ))
            
            logger.info(f"Discovered {len(documents)} ACS documents")
            return documents
            
        except Exception as e:
            logger.error(f"Error discovering documents: {e}")
            return []
    
    def load_known_documents(self) -> List[ACSDocument]:
        """Load previously known documents from metadata"""
        metadata_file = self.metadata_dir / "known_documents.json"
        
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    data = json.load(f)
                    return [ACSDocument(**doc) for doc in data]
            except Exception as e:
                logger.error(f"Error loading known documents: {e}")
        
        return []
    
    def save_known_documents(self, documents: List[ACSDocument]):
        """Save document metadata"""
        metadata_file = self.metadata_dir / "known_documents.json"
        
        try:
            with open(metadata_file, 'w') as f:
                json.dump([asdict(doc) for doc in documents], f, indent=2)
        except Exception as e:
            logger.error(f"Error saving known documents: {e}")
    
    def check_document_changes(self, document: ACSDocument) -> Tuple[bool, ACSDocument]:
        """Check if a document has changed"""
        logger.info(f"Checking {document.name}...")
        
        try:
            # Send HEAD request first to check headers
            head_response = self.session.head(document.url, timeout=30, allow_redirects=True)
            
            if head_response.status_code != 200:
                logger.warning(f"HEAD request failed for {document.name}: {head_response.status_code}")
                return False, document
            
            # Check Last-Modified header
            last_modified = head_response.headers.get('Last-Modified')
            etag = head_response.headers.get('ETag')
            content_length = head_response.headers.get('Content-Length')
            
            # Create updated document info
            updated_doc = ACSDocument(
                name=document.name,
                url=document.url,
                last_modified=last_modified,
                etag=etag,
                file_size=int(content_length) if content_length else None,
                last_checked=datetime.now().isoformat()
            )
            
            # Check for changes
            changed = False
            
            if document.last_modified != last_modified:
                logger.info(f"Last-Modified changed for {document.name}")
                changed = True
            
            if document.etag != etag:
                logger.info(f"ETag changed for {document.name}")
                changed = True
                
            if document.file_size != updated_doc.file_size:
                logger.info(f"File size changed for {document.name}")
                changed = True
            
            # If headers suggest change, download and check content hash
            if changed:
                logger.info(f"Downloading {document.name} to verify changes...")
                content_changed, updated_doc = self.download_and_verify(updated_doc)
                return content_changed, updated_doc
            
            return False, updated_doc
            
        except Exception as e:
            logger.error(f"Error checking {document.name}: {e}")
            return False, document
    
    def download_and_verify(self, document: ACSDocument) -> Tuple[bool, ACSDocument]:
        """Download document and verify content changes"""
        try:
            response = self.session.get(document.url, timeout=60)
            response.raise_for_status()
            
            # Calculate content hash
            content_hash = hashlib.sha256(response.content).hexdigest()
            
            # Create filename
            safe_name = "".join(c for c in document.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = f"{safe_name}.pdf"
            local_path = self.docs_dir / filename
            
            # Check if content actually changed
            if document.content_hash == content_hash:
                logger.info(f"Content hash unchanged for {document.name}")
                return False, document
            
            # Save the document
            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            # Update document metadata
            document.content_hash = content_hash
            document.local_path = str(local_path)
            
            logger.info(f"Downloaded updated {document.name}")
            return True, document
            
        except Exception as e:
            logger.error(f"Error downloading {document.name}: {e}")
            return False, document
    
    def monitor(self):
        """Main monitoring function"""
        logger.info("Starting FAA ACS monitoring...")
        
        # Load known documents
        known_docs = self.load_known_documents()
        known_urls = {doc.url: doc for doc in known_docs}
        
        # Discover current documents
        current_docs = self.discover_acs_documents()
        
        changes = []
        all_docs = []
        
        for doc in current_docs:
            # Rate limiting - be respectful to FAA servers
            time.sleep(2)
            
            if doc.url in known_urls:
                # Check existing document for changes
                changed, updated_doc = self.check_document_changes(known_urls[doc.url])
                if changed:
                    changes.append({
                        'type': 'updated',
                        'document': asdict(updated_doc),
                        'timestamp': datetime.now().isoformat()
                    })
                all_docs.append(updated_doc)
            else:
                # New document discovered
                logger.info(f"New document discovered: {doc.name}")
                _, downloaded_doc = self.download_and_verify(doc)
                changes.append({
                    'type': 'new',
                    'document': asdict(downloaded_doc),
                    'timestamp': datetime.now().isoformat()
                })
                all_docs.append(downloaded_doc)
        
        # Save updated metadata
        self.save_known_documents(all_docs)
        
        # Save changes log
        if changes:
            changes_file = self.metadata_dir / "changes.json"
            with open(changes_file, 'w') as f:
                json.dump(changes, f, indent=2)
            
            logger.info(f"Detected {len(changes)} changes")
        else:
            logger.info("No changes detected")
        
        # Generate summary
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_documents': len(all_docs),
            'changes_detected': len(changes),
            'changes': changes
        }
        
        summary_file = self.metadata_dir / "last_run_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info("Monitoring complete")

def main():
    """Main entry point"""
    monitor = FAAMonitor()
    monitor.monitor()

if __name__ == "__main__":
    main()