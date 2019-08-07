using System;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Text;

namespace PDFSanitizer
{
    public class FileManager
    {
        private WebClient _webClient;
        public IEnumerable<byte> FileBytes { get; set; }
        public string ConvertedGetUrl { get; set; }
        public string ConvertedPutUrl { get; set; }
        public Guid FileId { get; set; }
        public string FileName { get; set; }

        public FileManager(string fileUrl, string convertedGetUrl, string convertedPutUrl)
        {
            FileId = Guid.NewGuid();
            ConvertedGetUrl = convertedGetUrl;
            ConvertedPutUrl = convertedPutUrl;
            _webClient = new WebClient();
            if (!String.IsNullOrEmpty(fileUrl))
            {
                try
                {
                    FileBytes = _webClient.DownloadData(fileUrl);
                }
                catch (Exception e)
                {
                    Console.WriteLine($"Something went wrong while trying to download the file. " +
                                      $"Url: {fileUrl} " +
                                      $"Exception Message: {e.Message} " +
                                      $"StackTrace: {e.StackTrace}");
                }
            }
        }

        public byte GetByte()
        {

        }
    }
}
