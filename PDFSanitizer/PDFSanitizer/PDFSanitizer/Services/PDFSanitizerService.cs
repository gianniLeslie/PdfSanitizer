using System;
using System.Collections.Generic;
using System.Diagnostics.Tracing;
using System.Text;

namespace PDFSanitizer.Services
{

    public class PDFSanitizerService: IPDFSanitizerService
    {

        private string _word;
        private IEnumerable<char> _wordExact;
        private string _lastName;
        private string slash = "";
        private bool _insideStream;
        private bool _hexCode;
        private char digit1;
        private char digit2;
        private Dictionary<string, IEnumerable<int>> _words;
        private readonly IEnumerable<string> keywords = new List<string> {"obj", "endobj", "stream", "endstream", "xref", "trailer", "startxref", 
            "/Page", "/Encrypt", "ObjStm", "/JS", "/JavaScript", "/AA", "/OpenAction", "AcroForm", "JBIG2Decode", "RichMedia", "Launch", "EmbeddedFile", "/XFA"}; 

        public PDFSanitizerService()
        {
        }
    }

    
}
