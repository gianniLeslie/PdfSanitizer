using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;

namespace PDFSanitizer
{
    public static class Utilities
    {
        public static readonly ASCIIEncoding Encoding = new ASCIIEncoding();

        public static string SwapName(string word)
        {
            return String.Empty;
        }

        public static char SwapCase(char character)
        {
            return character;
        }
        public static void UpdateWords(string word, string wordExact, bool slash, List<string> words, bool hexcode,
            object allNames, object insideStream, object outputFile)
        {

        }

        public static string HexcodeToString(byte [] bytes)
        {
            return String.Empty;
        }

        public static IEnumerable<byte> StringToBytes(string words)
        {
            return Enumerable.Empty<byte>();
        }
    }
}
