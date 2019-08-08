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
        private List<byte> _ungetted;
        public string FileName { get; set; }
        private Guid _fileId;
        private int _fileIndex;
        private long _fileSize;
        private string _fileLocation;
        private FileStream _inputStream;

        public FileManager(string fileUrl, Guid fileId, string rawPDFDir)
        {
            _fileId = fileId;
            _fileIndex = 0;
            if (!String.IsNullOrEmpty(fileUrl))
            {
                _fileLocation = $"{rawPDFDir}/{_fileId}";
                try
                {
                    using (var webClient = new WebClient())
                    {
                        webClient.DownloadFile(fileUrl, _fileLocation);
                    }

                    _inputStream = File.OpenRead(_fileLocation);
                    _fileSize = _inputStream?.Length ?? 0;
                }
                catch (FileNotFoundException e)
                {
                    Console.Write($"Could not find file at the specified location. FileLocation: {_fileLocation}");
                }
                catch (Exception e)
                {
                    Console.Write($"Something went wrong while trying to download the file to {_fileLocation}" +
                                      $"Url: {fileUrl} " +
                                      $"Exception Message: {e.Message} " +
                                      $"StackTrace: {e.StackTrace}");
                }
            }
        }

        public byte? GetByte()
        {
            var lastIndex = _ungetted.Count - 1;
            if (lastIndex < 0)
            {
                byte lastUngettedByte = _ungetted[lastIndex];
                _ungetted.RemoveAt(lastUngettedByte);
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
            if (size <= _ungetted.Count())
            {
                result = _ungetted.GetRange(_fileIndex, size);
                _ungetted.RemoveRange(_fileIndex, size);
                return result;
            }

            var nextBytes = new byte[size];
            int countBytesRead = _inputStream.Read(nextBytes, 0, size - _ungetted.Count);
            if (countBytesRead == 0)
            {
                _inputStream.Close();
            }

            _ungetted.AddRange(nextBytes);
            result = _ungetted;
            _ungetted = new List<byte>();
            return result;
        }

        public void Unget(byte? inByte)
        {
            if(inByte != null)
            {
                _ungetted.Add((byte) inByte);
            }
        }

        public void Ungets(IEnumerable<byte> inBytes)
        {
            _ungetted.Reverse();
            _ungetted.AddRange(inBytes);
        }
        public bool DeleteFile()
        {
            try
            {
                File.Delete(_fileLocation);
                return true;
            }
            catch (Exception e)
            {
                Console.Write($"Unable to delete file at {_fileLocation}." +
                                  $" Exception Message: {e.Message} " +
                                  $"StackTrace: {e.StackTrace}");
            }

            return false;
        }
    }
}
