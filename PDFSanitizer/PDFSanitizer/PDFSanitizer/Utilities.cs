using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;

namespace PDFSanitizer
{
    public static class Utilities
    {
        public static readonly ASCIIEncoding Encoding = new ASCIIEncoding();

        public static string SwapName(List<char> wordExact)
        {
            string output = string.Empty;
            wordExact.ForEach(o => output.Append(SwapCase(o)));
            return output;
        }

        public static char SwapCase(char character)
        {
            return $"{character}".ToUpper().FirstOrDefault();
        }

        public static string ByteToString(byte b)
        {
            return Encoding.GetString(new byte[] {b});
        }

        public static byte[] StringToBytes(string word)
        {
            return Encoding.GetBytes(word);
        }
    }
}
