# FAA ACS Document Monitoring System 🛩️

Automated monitoring system for FAA Airman Certification Standards (ACS) documents with change detection and structured data extraction.

## 🚀 Features

- **Automated Discovery**: Finds all ACS documents from FAA website
- **Smart Change Detection**: Multiple methods (HTTP headers, content hashing, file size)
- **Modern PDF Processing**: 2024-2025 best practices with AI-optimized libraries
- **ACS-Specific Parsing**: Extracts Areas of Operation, Tasks, and References
- **GitHub Integration**: Automatic issues created when changes detected
- **Ethical Scraping**: Respects robots.txt, implements rate limiting

## 📁 Structure

```
faa-acs-monitor/
├── .github/workflows/
│   └── monitor-acs.yml          # GitHub Actions automation
├── scripts/
│   ├── monitor.py              # Main monitoring script
│   ├── pdf_processor.py        # PDF text extraction
│   └── create_change_notification.py  # GitHub notifications
├── data/                       # Generated data (auto-created)
│   ├── acs-documents/          # Downloaded PDFs
│   ├── extracted-text/         # Parsed content
│   └── metadata/               # Document metadata
├── requirements.txt            # Python dependencies
└── setup.md                   # Detailed setup guide
```

## 🛠️ Quick Start

1. **Fork this repository**
2. **Enable GitHub Actions** in your repository settings
3. **Enable Issues** for notifications
4. **Wait for the scheduled run** (Mondays 9 AM EST) or trigger manually

## 📊 What Happens

When changes are detected:
1. Downloads updated PDF
2. Extracts structured text using AI-optimized libraries
3. Parses ACS-specific content
4. Creates GitHub Issue with change details
5. Commits new data to repository

## 🔧 Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Run monitoring
python scripts/monitor.py

# Process PDFs
python scripts/pdf_processor.py
```

## 💰 Cost

**FREE** - Uses GitHub Actions (2,000 minutes/month included)

## 📖 Documentation

See [setup.md](setup.md) for complete setup instructions and technical details.

## 🤝 Contributing

Contributions welcome! Please read the setup guide first.

## 📄 License

MIT License - see LICENSE file for details.

---

*Built with 2024-2025 best practices for web automation and PDF processing.*