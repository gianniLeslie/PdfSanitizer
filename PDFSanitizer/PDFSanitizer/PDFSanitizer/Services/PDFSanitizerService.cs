using System;
using System.Collections.Generic;
using System.Diagnostics.Tracing;
using System.IO;
using System.Linq;
using System.Net;
using System.Text;

namespace PDFSanitizer.Services
{

    public class PDFSanitizerService : IPDFSanitizerService
    {
        private readonly IEnumerable<string> keywords = new List<string> {"obj", "endobj", "stream", "endstream", "xref", "trailer", "startxref",
            "/Page", "/Encrypt", "ObjStm", "/JS", "/JavaScript", "/AA", "/OpenAction", "AcroForm", "JBIG2Decode", "RichMedia", "Launch", "EmbeddedFile", "/XFA"};
        private readonly IEnumerable<string> _badKeywords = new List<string> { "/JS", "/JavaScript", "/AA", "/OpenAction", "/JBIG2Decode", "/RichMedia", "/Launch" };
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
            PDFInfoModel pdfInfo = new PDFInfoModel
            {
                HexCode = false,
                Word = String.Empty,
                WordExact = new List<char>(),
                LastName = String.Empty,
                Slash = Char.MinValue,

            };
            Guid fileId = Guid.NewGuid();
            byte? digit1 = null;
            byte? digit2 = null;

            string _outputFilePath = $"{_convertedFileDirectory}/{fileId}.disarmed.pdf";
            Dictionary<string, IEnumerable<int>> _words;
            //Get source file
            var rawFileManager = new FileManager(fileUrl, fileId, _rawFileDirectory);
            try
            {
                //Create destination file
                System.IO.File.Create(_outputFilePath);
                using (var outputFile = System.IO.File.OpenWrite(_outputFilePath))
                {
                    //Read and disarm
                    byte? currentByte = rawFileManager.GetByte();
                    while (currentByte != null)
                    {
                        string currentString = Utilities.ByteToString((byte) currentByte);
                        char currentChar = currentString[0];
                        char currentCharUpper = currentString.ToUpper()[0];
                        if ((currentCharUpper >= 'A' && currentCharUpper <= 'Z')
                            || (currentCharUpper >= '0' && currentCharUpper <= '9'))
                        {
                            pdfInfo.Word += currentString[0];
                            pdfInfo.WordExact.Add(currentString[0]);
                        }
                        else if (pdfInfo.Slash == '/' && currentChar == '#')
                        {
                            //Checking for hexcode
                            digit1 = rawFileManager.GetByte();
                            digit2 = digit1 != null ? rawFileManager.GetByte() : null;
                            if (digit2 != null)
                            {
                                string digit1String = Utilities.ByteToString((byte) digit1);
                                string digit2String = Utilities.ByteToString((byte) digit2);
                                char digit1Char = digit1String.FirstOrDefault();
                                char digit2Char = digit2String.FirstOrDefault();
                                char digit1CharUpper = digit1String.ToUpper().FirstOrDefault();
                                char digit2CharUpper = digit2String.ToUpper().FirstOrDefault();

                                if (((digit1Char >= '0' && digit1Char <= '9') ||
                                     (digit1CharUpper >= 'A' && digit1CharUpper <= 'F'))
                                    && (digit2Char >= '0' && digit2Char <= '9') ||
                                    (digit2CharUpper >= 'A' && digit2CharUpper <= 'F'))
                                {
                                    pdfInfo.HexCode = true;
                                    string hexString = $"{digit1Char}{digit2Char}";
                                    char hexChar = (char) int.Parse(hexString,
                                        System.Globalization.NumberStyles.HexNumber);
                                    pdfInfo.Word += hexChar;
                                    pdfInfo.WordExact.Add(hexChar);
                                }
                                else
                                {
                                    rawFileManager.Unget(digit1);
                                    rawFileManager.Unget(digit2);
                                    UpdateWords(pdfInfo, outputFile);
                                    outputFile.WriteByte((byte) currentByte);

                                }
                            }
                            else
                            {
                                rawFileManager.Unget(digit1);
                                UpdateWords(pdfInfo, outputFile);
                                if (digit1 != null)
                                {
                                    outputFile.WriteByte((byte) digit1);
                                }
                            }
                        }
                        else
                        {
                            //Add check for when the number of colors is expressed with more than 3 bytes
                            UpdateWords(pdfInfo, outputFile);
                            pdfInfo.Slash = currentChar == '/' ? '/' : Char.MinValue;
                            outputFile.WriteByte((byte) currentByte);
                        }

                        currentByte = rawFileManager.GetByte();
                    }

                    UpdateWords(pdfInfo, outputFile);
                }
            }
            catch (Exception e)
            {
                Console.WriteLine($"Something went wrong while sanitizing the pdf. " +
                                  $" Exception Message: {e.Message} " +
                                  $" StackTrace: {e.StackTrace} ");
            }
            finally
            {
                rawFileManager.DeleteFile();
            }

            return _outputFilePath;
        }

        private void UpdateWords(PDFInfoModel pdfInfo, FileStream outputFile)
        {
            if (pdfInfo.Word != String.Empty)
            {
                if (pdfInfo.Slash == '/')
                {
                    pdfInfo.LastName = pdfInfo.Slash + pdfInfo.Word;
                }
                else if (pdfInfo.Word == "stream")
                {
                    //Not needed for now but possibly for expanding features
                    pdfInfo.InsideStream = true;
                }
                else if (pdfInfo.Word == "endstream")
                {
                    pdfInfo.InsideStream = false;
                }

                if (outputFile != null)
                {
                    if (pdfInfo.Slash == '/' && _badKeywords.Contains(pdfInfo.Slash + pdfInfo.Word))
                    {
                        string wordExactSwapped = Utilities.SwapName(pdfInfo.WordExact);
                        outputFile.Write(Utilities.StringToBytes(wordExactSwapped));
                        Console.WriteLine($"Found a risky keyword. Swapped the casing. See? {wordExactSwapped}");
                    }
                    else
                    {
                        var outWord = String.Empty;
                        pdfInfo.WordExact.ForEach(o => outWord.Append(o));
                        outputFile.Write(Utilities.StringToBytes(outWord));
                    }
                }
            }

            pdfInfo.Word = String.Empty;
            pdfInfo.WordExact = new List<char>();
            pdfInfo.HexCode = false;
        }

    }

    internal class PDFInfoModel
    {
        public string Word { get; set; }
        public List<char> WordExact { get; set; }
        public string LastName { get; set; }
        public char Slash { get; set; }
        public bool InsideStream { get; set; }
        public bool HexCode { get; set; }

        public PDFInfoModel()
        {
            HexCode = false;
            InsideStream = false;
            Word = String.Empty;
            LastName = String.Empty;
            Slash = Char.MinValue;
            WordExact = new List<char>();
        }

    }
}
