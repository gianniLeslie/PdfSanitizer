using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Text;

namespace PDFSanitizer
{
    public class FileManager
    {
        public List<byte> Ungetted { get; set; }
        public string ConvertedGetUrl { get; set; }
        public string ConvertedPutUrl { get; set; }
        public string FileName { get; set; }
        private Guid _fileId { get; set; }
        private int _fileIndex { get; set; }
        private long _fileSize { get; set; }
        private FileStream _inputStream;

        public FileManager(string fileUrl, string rawPDFDir, string convertedPDFDir, string convertedGetUrl, string convertedPutUrl)
        {
            _fileId = Guid.NewGuid();
            _fileIndex = 0;
           
            ConvertedGetUrl = convertedGetUrl;
            ConvertedPutUrl = convertedPutUrl;
            if (!String.IsNullOrEmpty(fileUrl))
            {
                string rawFileLocation = $"{rawPDFDir}/{_fileId}";
                try
                {
                    using (var webClient = new WebClient())
                    {
                        webClient.DownloadFile(fileUrl, rawFileLocation);
                    }

                    _inputStream = File.OpenRead(rawFileLocation);
                    _fileSize = _inputStream?.Length ?? 0;
                }
                catch (FileNotFoundException e)
                {
                    Console.WriteLine($"Could not find file at the specified location. FileLocation: {rawFileLocation}");
                }
                catch (Exception e)
                {
                    Console.WriteLine($"Something went wrong while trying to download the file to {rawFileLocation}" +
                                      $"Url: {fileUrl} " +
                                      $"Exception Message: {e.Message} " +
                                      $"StackTrace: {e.StackTrace}");
                }
            }
        }

        public byte? GetByte()
        {
            var lastIndex = Ungetted.Count - 1;
            if (lastIndex < 0)
            {
                byte lastUngettedByte = Ungetted[lastIndex];
                Ungetted.RemoveAt(lastUngettedByte);
                return lastUngettedByte;
            }

            if (_fileIndex < _fileSize - 1)
            {
                return (byte) _inputStream.ReadByte();
            }

            _inputStream.Close();
            return null;
        }

        public IEnumerable<byte> GetBytes(int size)
        {
            List<byte> result;
            if (size <= Ungetted.Count())
            {
                result = Ungetted.GetRange(_fileIndex, size);
                Ungetted.RemoveRange(_fileIndex, size);
                return result;
            }

            var nextBytes = new byte[size];
            int countBytesRead = _inputStream.Read(nextBytes, 0, size - Ungetted.Count);
            if (countBytesRead == 0)
            {
                _inputStream.Close();
            }

            Ungetted.AddRange(nextBytes);
            result = Ungetted;
            Ungetted = new List<byte>();
            return result;
        }

        public void Unget(byte inByte)
        {
            Ungetted.Add(inByte);
        }

        public void Ungets(IEnumerable<byte> inBytes)
        {
            Ungetted.Reverse();
            Ungetted.AddRange(inBytes);
        }
        public bool DeleteFile()
        {
            return false;
        }
    }
}
