using System;
using System.Collections.Generic;
using System.Diagnostics.Tracing;
using System.Linq;
using System.Net;
using System.Text;

namespace PDFSanitizer.Services
{

    public class PDFSanitizerService : IPDFSanitizerService
    {
        private readonly IEnumerable<string> keywords = new List<string> {"obj", "endobj", "stream", "endstream", "xref", "trailer", "startxref",
            "/Page", "/Encrypt", "ObjStm", "/JS", "/JavaScript", "/AA", "/OpenAction", "AcroForm", "JBIG2Decode", "RichMedia", "Launch", "EmbeddedFile", "/XFA"};
        private readonly string _rawFileDirectory;
        private readonly string _convertedFileDirectory;

        public PDFSanitizerService(string rawFileDirectory, string convertedFileDirectory)
        {
            _rawFileDirectory = rawFileDirectory;
            _convertedFileDirectory = convertedFileDirectory;
        }

        public string SanitizePdf(string fileUrl, string convertedGetUrl, string convertedPutUrl)
        {
            //Setup
            Guid fileId = Guid.NewGuid();
            string word = String.Empty;
            List<char> wordExact = new List<char>();
            string _lastName;
            char slash = Char.MinValue;
            bool insideStream;
            bool hexCode;
            byte? digit1;
            byte? digit2;
            string _outputFilePath = $"{_convertedFileDirectory}/{fileId}.disarmed.pdf";
            Dictionary<string, IEnumerable<int>> _words;
            //Get source file
            var rawFileManager = new FileManager(fileUrl, fileId, _rawFileDirectory);
            //Create destination file
            System.IO.File.Create(_outputFilePath);
            using (var outputFile = System.IO.File.OpenWrite(_outputFilePath))
            {
                //Read and disarm
                byte? currentByte = rawFileManager.GetByte();
                while (currentByte != null)
                {
                    string currentString = Utilities.ByteToString((byte)currentByte);
                    char currentChar = currentString[0];
                    char currentCharUpper = currentString.ToUpper()[0];
                    if ((currentCharUpper >= 'A' && currentCharUpper <= 'Z')
                        || (currentCharUpper >= '0' && currentCharUpper <= '9'))
                    {
                        word += currentString[0];
                        wordExact.Add(currentString[0]);
                    }
                    else if (slash == '/' && currentChar == '#')
                    {
                        //Checking for hexcode
                        digit1 = rawFileManager.GetByte();
                        digit2 = digit1 != null ? rawFileManager.GetByte() : null;
                        if (digit2 != null)
                        {
                            string digit1String = Utilities.ByteToString((byte)digit1);
                            string digit2String = Utilities.ByteToString((byte)digit2);
                            char digit1Char = digit1String.FirstOrDefault();
                            char digit2Char = digit2String.FirstOrDefault();
                            char digit1CharUpper = digit1String.ToUpper().FirstOrDefault();
                            char digit2CharUpper = digit2String.ToUpper().FirstOrDefault();

                            if (((digit1Char >= '0' && digit1Char <= '9') || (digit1CharUpper >= 'A' && digit1CharUpper <= 'F'))
                                && (digit2Char >= '0' && digit2Char <= '9') || (digit2CharUpper >= 'A' && digit2CharUpper <= 'F'))
                            {
                                hexCode = true;
                                string hexString = $"{digit1Char}{digit2Char}";
                                char hexChar = (char)Int32.Parse(hexString, System.Globalization.NumberStyles.HexNumber);
                                word += hexChar;
                                wordExact.Add(hexChar);
                            }
                            else
                            {
                                rawFileManager.Unget(digit1);
                                rawFileManager.Unget(digit2);
                                UpdateWords();
                                outputFile.WriteByte((byte) currentByte);

                            }
                        }
                        else 
                        {
                            rawFileManager.Unget(digit1);
                            UpdateWords();
                            if (digit1 != null)
                            {
                                outputFile.WriteByte((byte) digit1);
                            }
                        }
                    }
                    else
                    {
                        UpdateWords();
                        if (currentChar == '/')
                        {
                            slash = '/';
                        }
                        else
                        {
                            slash = Char.MinValue;
                        }

                        outputFile.WriteByte((byte) currentByte);
                    }

                    currentByte = rawFileManager.GetByte();
                }

                UpdateWords();
            }

            return _outputFilePath;
        }

        public bool UpdateWords()
        {
            return false;
        }
    }


}
