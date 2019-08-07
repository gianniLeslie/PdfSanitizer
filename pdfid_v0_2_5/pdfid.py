#!/usr/bin/env python

__description__ = 'Tool to test a PDF file'
__author__ = 'Didier Stevens'
__version__ = '0.2.5'
__date__ = '2018/07/05'

"""

Tool to test a PDF file

Source code put in public domain by Didier Stevens, no Copyright
https://DidierStevens.com
Use at your own risk

History:
  2009/03/27: start
  2009/03/28: scan option
  2009/03/29: V0.0.2: xml output
  2009/03/31: V0.0.3: /ObjStm suggested by Dion
  2009/04/02: V0.0.4: added ErrorMessage
  2009/04/20: V0.0.5: added Dates
  2009/04/21: V0.0.6: added entropy
  2009/04/22: added disarm
  2009/04/29: finished disarm
  2009/05/13: V0.0.7: added cPDFEOF
  2009/07/24: V0.0.8: added /AcroForm and /RichMedia, simplified %PDF header regex, extra date format (without TZ)
  2009/07/25: added input redirection, option --force
  2009/10/13: V0.0.9: added detection for CVE-2009-3459; added /RichMedia to disarm
  2010/01/11: V0.0.10: relaxed %PDF header checking
  2010/04/28: V0.0.11: added /Launch
  2010/09/21: V0.0.12: fixed cntCharsAfterLastEOF bug; fix by Russell Holloway
  2011/12/29: updated for Python 3, added keyword /EmbeddedFile
  2012/03/03: added PDFiD2JSON; coded by Brandon Dixon
  2013/02/10: V0.1.0: added http/https support; added support for ZIP file with password 'infected'
  2013/03/11: V0.1.1: fixes for Python 3
  2013/03/13: V0.1.2: Added error handling for files; added /XFA
  2013/11/01: V0.2.0: Added @file & plugins
  2013/11/02: continue
  2013/11/04: added options -c, -m, -v
  2013/11/06: added option -S
  2013/11/08: continue
  2013/11/09: added option -o
  2013/11/15: refactoring
  2014/09/30: added CSV header
  2014/10/16: V0.2.1: added output when plugin & file not pdf
  2014/10/18: some fixes for Python 3
  2015/08/12: V0.2.2: added option pluginoptions
  2015/08/13: added plugin Instructions method
  2016/04/12: added option literal
  2017/10/29: added pdfid.ini support
  2017/11/05: V0.2.3: added option -n
  2018/01/03: V0.2.4: bugfix entropy calculation for PDFs without streams; sample 28cb208d976466b295ee879d2d233c8a https://twitter.com/DubinRan/status/947783629123416069
  2018/01/15: bugfix ConfigParser privately reported
  2018/01/29: bugfix oPDFEOF.cntCharsAfterLastEOF when no %%EOF
  2018/07/05: V0.2.5 introduced cExpandFilenameArguments; renamed option literal to literalfilenames

Todo:
  - update XML example (entropy, EOF)
  - code review, cleanup
"""

import optparse
import os
import re
import xml.dom.minidom
import traceback
import math
import operator
import os.path
import sys
import json
import zipfile
import collections
import glob
import fnmatch
if sys.version_info[0] >= 3:
    import urllib.request as urllib23
else:
    import urllib2 as urllib23
if sys.version_info[0] >= 3:
    import configparser as ConfigParser
else:
    import ConfigParser

#Convert 2 Bytes If Python 3
def C2BIP3(string):
    if sys.version_info[0] > 2:
        return bytes([ord(x) for x in string])
    else:
        return string

class cBinaryFile:
    def __init__(self, file):
        self.file = file
        if file == '':
            self.infile = sys.stdin
        elif file.lower().startswith('http://') or file.lower().startswith('https://'):
            try:
                if sys.hexversion >= 0x020601F0:
                    self.infile = urllib23.urlopen(file, timeout=5)
                else:
                    self.infile = urllib23.urlopen(file)
            except urllib23.HTTPError:
                print('Error accessing URL %s' % file)
                print(sys.exc_info()[1])
                sys.exit()
        elif file.lower().endswith('.zip'):
            try:
                self.zipfile = zipfile.ZipFile(file, 'r')
                self.infile = self.zipfile.open(self.zipfile.infolist()[0], 'r', C2BIP3('infected'))
            except:
                print('Error opening file %s' % file)
                print(sys.exc_info()[1])
                sys.exit()
        else:
            try:
                self.infile = open(file, 'rb')
            except:
                print('Error opening file %s' % file)
                print(sys.exc_info()[1])
                sys.exit()
        self.ungetted = []

    def byte(self):
        if len(self.ungetted) != 0:
            return self.ungetted.pop()
        inbyte = self.infile.read(1)
        if not inbyte or inbyte == '':
            self.infile.close()
            return None
        return ord(inbyte)

    def bytes(self, size):
        if size <= len(self.ungetted):
            result = self.ungetted[0:size]
            del self.ungetted[0:size]
            return result
        inbytes = self.infile.read(size - len(self.ungetted))
        if inbytes == '':
            self.infile.close()
        if type(inbytes) == type(''):
            result = self.ungetted + [ord(b) for b in inbytes]
        else:
            result = self.ungetted + [b for b in inbytes]
        self.ungetted = []
        return result

    def unget(self, byte):
        self.ungetted.append(byte)

    def ungets(self, bytes):
        bytes.reverse()
        self.ungetted.extend(bytes)

class cPDFDate:
    def __init__(self):
        self.state = 0

    def parse(self, char):
        if char == 'D':
            self.state = 1
            return None
        elif self.state == 1:
            if char == ':':
                self.state = 2
                self.digits1 = ''
            else:
                self.state = 0
            return None
        elif self.state == 2:
            if len(self.digits1) < 14:
                if char >= '0' and char <= '9':
                    self.digits1 += char
                    return None
                else:
                    self.state = 0
                    return None
            elif char == '+' or char == '-' or char == 'Z':
                self.state = 3
                self.digits2 = ''
                self.TZ = char
                return None
            elif char == '"':
                self.state = 0
                self.date = 'D:' + self.digits1
                return self.date
            elif char < '0' or char > '9':
                self.state = 0
                self.date = 'D:' + self.digits1
                return self.date
            else:
                self.state = 0
                return None
        elif self.state == 3:
            if len(self.digits2) < 2:
                if char >= '0' and char <= '9':
                    self.digits2 += char
                    return None
                else:
                    self.state = 0
                    return None
            elif len(self.digits2) == 2:
                if char == "'":
                    self.digits2 += char
                    return None
                else:
                    self.state = 0
                    return None
            elif len(self.digits2) < 5:
                if char >= '0' and char <= '9':
                    self.digits2 += char
                    if len(self.digits2) == 5:
                        self.state = 0
                        self.date = 'D:' + self.digits1 + self.TZ + self.digits2
                        return self.date
                    else:
                        return None
                else:
                    self.state = 0
                    return None

class cPDFEOF:
    def __init__(self):
        self.token = ''
        self.cntEOFs = 0

    def parse(self, char):
        if self.cntEOFs > 0:
            self.cntCharsAfterLastEOF += 1
        if self.token == '' and char == '%':
            self.token += char
            return
        elif self.token == '%' and char == '%':
            self.token += char
            return
        elif self.token == '%%' and char == 'E':
            self.token += char
            return
        elif self.token == '%%E' and char == 'O':
            self.token += char
            return
        elif self.token == '%%EO' and char == 'F':
            self.token += char
            return
        elif self.token == '%%EOF' and (char == '\n' or char == '\r' or char == ' ' or char == '\t'):
            self.cntEOFs += 1
            self.cntCharsAfterLastEOF = 0
            if char == '\n':
                self.token = ''
            else:
                self.token += char
            return
        elif self.token == '%%EOF\r':
            if char == '\n':
                self.cntCharsAfterLastEOF = 0
            self.token = ''
        else:
            self.token = ''

def FindPDFHeaderRelaxed(oBinaryFile):
    bytes = oBinaryFile.bytes(1024)
    index = ''.join([chr(byte) for byte in bytes]).find('%PDF')
    if index == -1:
        oBinaryFile.ungets(bytes)
        return ([], None)
    for endHeader in range(index + 4, index + 4 + 10):
        if bytes[endHeader] == 10 or bytes[endHeader] == 13:
            break
    oBinaryFile.ungets(bytes[endHeader:])
    return (bytes[0:endHeader], ''.join([chr(byte) for byte in bytes[index:endHeader]]))

def Hexcode2String(char):
    if type(char) == int:
        return '#%02x' % char
    else:
        return char

def SwapCase(char):
    if type(char) == int:
        return ord(chr(char).swapcase())
    else:
        return char.swapcase()

def HexcodeName2String(hexcodeName):
    return ''.join(map(Hexcode2String, hexcodeName))

def SwapName(wordExact):
    return map(SwapCase, wordExact)

def UpdateWords(word, wordExact, slash, words, hexcode, allNames, lastName, insideStream, oEntropy, fOut):
    if word != '':
        if slash + word in words:
            words[slash + word][0] += 1
            if hexcode:
                words[slash + word][1] += 1
        elif slash == '/' and allNames:
            words[slash + word] = [1, 0]
            if hexcode:
                words[slash + word][1] += 1
        if slash == '/':
            lastName = slash + word
        if slash == '':
            if word == 'stream':
                insideStream = True
            if word == 'endstream':
                if insideStream == True and oEntropy != None:
                    for char in 'endstream':
                        oEntropy.removeInsideStream(ord(char))
                insideStream = False
        if fOut != None:
            if slash == '/' and '/' + word in ('/JS', '/JavaScript', '/AA', '/OpenAction', '/JBIG2Decode', '/RichMedia', '/Launch'):
                wordExactSwapped = HexcodeName2String(SwapName(wordExact))
                fOut.write(C2BIP3(wordExactSwapped))
                print('/%s -> /%s' % (HexcodeName2String(wordExact), wordExactSwapped))
            else:
                fOut.write(C2BIP3(HexcodeName2String(wordExact)))
    return ('', [], False, lastName, insideStream)

class cCVE_2009_3459:
    def __init__(self):
        self.count = 0

    def Check(self, lastName, word):
        if (lastName == '/Colors' and word.isdigit() and int(word) > 2^24): # decided to alert when the number of colors is expressed with more than 3 bytes
            self.count += 1


def PDFiD(file, allNames=False, extraData=False, disarm=False, force=False):
    """Example of XML output:
    <PDFiD ErrorOccured="False" ErrorMessage="" Filename="test.pdf" Header="%PDF-1.1" IsPDF="True" Version="0.0.4" Entropy="4.28">
            <Keywords>
                    <Keyword Count="7" HexcodeCount="0" Name="obj"/>
                    <Keyword Count="7" HexcodeCount="0" Name="endobj"/>
                    <Keyword Count="1" HexcodeCount="0" Name="stream"/>
                    <Keyword Count="1" HexcodeCount="0" Name="endstream"/>
                    <Keyword Count="1" HexcodeCount="0" Name="xref"/>
                    <Keyword Count="1" HexcodeCount="0" Name="trailer"/>
                    <Keyword Count="1" HexcodeCount="0" Name="startxref"/>
                    <Keyword Count="1" HexcodeCount="0" Name="/Page"/>
                    <Keyword Count="0" HexcodeCount="0" Name="/Encrypt"/>
                    <Keyword Count="1" HexcodeCount="0" Name="/JS"/>
                    <Keyword Count="1" HexcodeCount="0" Name="/JavaScript"/>
                    <Keyword Count="0" HexcodeCount="0" Name="/AA"/>
                    <Keyword Count="1" HexcodeCount="0" Name="/OpenAction"/>
                    <Keyword Count="0" HexcodeCount="0" Name="/JBIG2Decode"/>
            </Keywords>
            <Dates>
                    <Date Value="D:20090128132916+01'00" Name="/ModDate"/>
            </Dates>
    </PDFiD>
    """

    word = ''
    wordExact = []
    hexcode = False
    lastName = ''
    insideStream = False
    keywords = ['obj',
                'endobj',
                'stream',
                'endstream',
                'xref',
                'trailer',
                'startxref',
                '/Page',
                '/Encrypt',
                '/ObjStm',
                '/JS',
                '/JavaScript',
                '/AA',
                '/OpenAction',
                '/AcroForm',
                '/JBIG2Decode',
                '/RichMedia',
                '/Launch',
                '/EmbeddedFile',
                '/XFA',
               ]
    words = {}
    dates = []
 
    for keyword in keywords:
        words[keyword] = [0, 0]
    slash = ''

    oPDFDate = None
    oEntropy = None
    oPDFEOF = None
    oCVE_2009_3459 = cCVE_2009_3459()
    try:
        oBinaryFile = cBinaryFile(file)

        (pathfile, extension) = os.path.splitext(file)
        fOut = open(pathfile + '.disarmed' + extension, 'wb')

        byte = oBinaryFile.byte()
        while byte != None:
            char = chr(byte)
            charUpper = char.upper()
            if charUpper >= 'A' and charUpper <= 'Z' or charUpper >= '0' and charUpper <= '9':
                word += char
                wordExact.append(char)
            elif slash == '/' and char == '#':
                d1 = oBinaryFile.byte()
                if d1 != None:
                    d2 = oBinaryFile.byte()
                    if d2 != None and (chr(d1) >= '0' and chr(d1) <= '9' or chr(d1).upper() >= 'A' and chr(d1).upper() <= 'F') and (chr(d2) >= '0' and chr(d2) <= '9' or chr(d2).upper() >= 'A' and chr(d2).upper() <= 'F'):
                        word += chr(int(chr(d1) + chr(d2), 16))
                        wordExact.append(int(chr(d1) + chr(d2), 16))
                        hexcode = True
                        if oEntropy != None:
                            oEntropy.add(d1, insideStream)
                            oEntropy.add(d2, insideStream)
                        if oPDFEOF != None:
                            oPDFEOF.parse(d1)
                            oPDFEOF.parse(d2)
                    else:
                        oBinaryFile.unget(d2)
                        oBinaryFile.unget(d1)
                        (word, wordExact, hexcode, lastName, insideStream) = UpdateWords(word, wordExact, slash, words, hexcode, allNames, lastName, insideStream, oEntropy, fOut)
                        if disarm:
                            fOut.write(C2BIP3(char))
                else:
                    oBinaryFile.unget(d1)
                    (word, wordExact, hexcode, lastName, insideStream) = UpdateWords(word, wordExact, slash, words, hexcode, allNames, lastName, insideStream, oEntropy, fOut)
                    if disarm:
                        fOut.write(C2BIP3(char))
            else:
                oCVE_2009_3459.Check(lastName, word)

                (word, wordExact, hexcode, lastName, insideStream) = UpdateWords(word, wordExact, slash, words, hexcode, allNames, lastName, insideStream, oEntropy, fOut)
                if char == '/':
                    slash = '/'
                else:
                    slash = ''
                if disarm:
                    fOut.write(C2BIP3(char))

            if oPDFDate != None and oPDFDate.parse(char) != None:
                dates.append([oPDFDate.date, lastName])

            if oEntropy != None:
                oEntropy.add(byte, insideStream)

            if oPDFEOF != None:
                oPDFEOF.parse(char)

            byte = oBinaryFile.byte()
        (word, wordExact, hexcode, lastName, insideStream) = UpdateWords(word, wordExact, slash, words, hexcode, allNames, lastName, insideStream, oEntropy, fOut)

        # check to see if file ended with %%EOF.  If so, we can reset charsAfterLastEOF and add one to EOF count.  This is never performed in
        # the parse function because it never gets called due to hitting the end of file.
        if byte == None and oPDFEOF != None:
            if oPDFEOF.token == '%%EOF':
                oPDFEOF.cntEOFs += 1
                oPDFEOF.cntCharsAfterLastEOF = 0
                oPDFEOF.token = ''

    except SystemExit:
        sys.exit()
    except:
        attErrorOccured.nodeValue = 'True'
        attErrorMessage.nodeValue = traceback.format_exc()

    fOut.close()

class cCount():
    def __init__(self, count, hexcode):
        self.count = count
        self.hexcode = hexcode

class cPDFiD():
    def __init__(self, xmlDoc, force):
        self.version = xmlDoc.documentElement.getAttribute('Version')
        self.filename = xmlDoc.documentElement.getAttribute('Filename')
        self.errorOccured = xmlDoc.documentElement.getAttribute('ErrorOccured') == 'True'
        self.errorMessage = xmlDoc.documentElement.getAttribute('ErrorMessage')
        self.isPDF = None
        if self.errorOccured:
            return
        self.isPDF = xmlDoc.documentElement.getAttribute('IsPDF') == 'True'
        if not force and not self.isPDF:
            return
        self.header = xmlDoc.documentElement.getAttribute('Header')
        self.keywords = {}
        for node in xmlDoc.documentElement.getElementsByTagName('Keywords')[0].childNodes:
            self.keywords[node.getAttribute('Name')] = cCount(int(node.getAttribute('Count')), int(node.getAttribute('HexcodeCount')))
        self.obj = self.keywords['obj']
        self.endobj = self.keywords['endobj']
        self.stream = self.keywords['stream']
        self.endstream = self.keywords['endstream']
        self.xref = self.keywords['xref']
        self.trailer = self.keywords['trailer']
        self.startxref = self.keywords['startxref']
        self.page = self.keywords['/Page']
        self.encrypt = self.keywords['/Encrypt']
        self.objstm = self.keywords['/ObjStm']
        self.js = self.keywords['/JS']
        self.javascript = self.keywords['/JavaScript']
        self.aa = self.keywords['/AA']
        self.openaction = self.keywords['/OpenAction']
        self.acroform = self.keywords['/AcroForm']
        self.jbig2decode = self.keywords['/JBIG2Decode']
        self.richmedia = self.keywords['/RichMedia']
        self.launch = self.keywords['/Launch']
        self.embeddedfile = self.keywords['/EmbeddedFile']
        self.xfa = self.keywords['/XFA']
        self.colors_gt_2_24 = self.keywords['/Colors > 2^24']

def Print(lines, options):
    print(lines)
    filename = None
    if options.scan:
        filename = 'PDFiD.log'
    if options.output != '':
        filename = options.output
    if filename:
        logfile = open(filename, 'a')
        logfile.write(lines + '\n')
        logfile.close()

def Quote(value, separator, quote):
    if isinstance(value, str):
        if separator in value:
            return quote + value + quote
    return value


def ProcessFile(filename, options, plugins):
    xmlDoc = PDFiD(filename, options.all, options.extra, options.disarm, options.force)
    if plugins == [] and options.select == '':
        Print(PDFiD2String(xmlDoc, options.nozero, options.force), options)
        return

    oPDFiD = cPDFiD(xmlDoc, options.force)
    if options.select:
        if options.force or not oPDFiD.errorOccured and oPDFiD.isPDF:
            pdf = oPDFiD
            try:
                selected = eval(options.select)
            except Exception as e:
                Print('Error evaluating select expression: %s' % options.select, options)
                if options.verbose:
                    raise e
                return
            if selected:
                if options.csv:
                    Print(filename, options)
                else:
                    Print(PDFiD2String(xmlDoc, options.nozero, options.force), options)
    else:
        for cPlugin in plugins:
            if not cPlugin.onlyValidPDF or not oPDFiD.errorOccured and oPDFiD.isPDF:
                try:
                    oPlugin = cPlugin(oPDFiD, options.pluginoptions)
                except Exception as e:
                    Print('Error instantiating plugin: %s' % cPlugin.name, options)
                    if options.verbose:
                        raise e
                    return

                try:
                    score = oPlugin.Score()
                except Exception as e:
                    Print('Error running plugin: %s' % cPlugin.name, options)
                    if options.verbose:
                        raise e
                    return

                if options.csv:
                    if score >= options.minimumscore:
                        Print(MakeCSVLine((('%s', filename), ('%s', cPlugin.name), ('%.02f', score))), options)
                else:
                    if score >= options.minimumscore:
                        Print(PDFiD2String(xmlDoc, options.nozero, options.force), options)
                        Print('%s score:        %.02f' % (cPlugin.name, score), options)
                        try:
                            Print('%s instructions: %s' % (cPlugin.name, oPlugin.Instructions(score)), options)
                        except AttributeError:
                            pass
            else:
                if options.csv:
                    if oPDFiD.errorOccured:
                        Print(MakeCSVLine((('%s', filename), ('%s', cPlugin.name), ('%s', 'Error occured'))), options)
                    if not oPDFiD.isPDF:
                        Print(MakeCSVLine((('%s', filename), ('%s', cPlugin.name), ('%s', 'Not a PDF document'))), options)
                else:
                    Print(PDFiD2String(xmlDoc, options.nozero, options.force), options)

def File2Strings(filename):
    try:
        f = open(filename, 'r')
    except:
        return None
    try:
        return list(map(lambda line:line.rstrip('\n'), f.readlines()))
    except:
        return None
    finally:
        f.close()

def ProcessAt(argument):
    if argument.startswith('@'):
        strings = File2Strings(argument[1:])
        if strings == None:
            raise Exception('Error reading %s' % argument)
        else:
            return strings
    else:
        return [argument]


class cExpandFilenameArguments():
    def __init__(self, filenames, literalfilenames=False, recursedir=False, checkfilenames=False, expressionprefix=None):
        self.containsUnixShellStyleWildcards = False
        self.warning = False
        self.message = ''
        self.filenameexpressions = []
        self.expressionprefix = expressionprefix
        self.literalfilenames = literalfilenames

        expression = ''
        if len(filenames) == 0:
            self.filenameexpressions = [['', '']]
        elif literalfilenames:
            self.filenameexpressions = [[filename, ''] for filename in filenames]
        elif recursedir:
            for dirwildcard in filenames:
                if expressionprefix != None and dirwildcard.startswith(expressionprefix):
                    expression = dirwildcard[len(expressionprefix):]
                else:
                    if dirwildcard.startswith('@'):
                        for filename in ProcessAt(dirwildcard):
                            self.filenameexpressions.append([filename, expression])
                    elif os.path.isfile(dirwildcard):
                        self.filenameexpressions.append([dirwildcard, expression])
                    else:
                        if os.path.isdir(dirwildcard):
                            dirname = dirwildcard
                            basename = '*'
                        else:
                            dirname, basename = os.path.split(dirwildcard)
                            if dirname == '':
                                dirname = '.'
                        for path, dirs, files in os.walk(dirname):
                            for filename in fnmatch.filter(files, basename):
                                self.filenameexpressions.append([os.path.join(path, filename), expression])
        else:
            for filename in list(collections.OrderedDict.fromkeys(sum(map(self.Glob, sum(map(ProcessAt, filenames), [])), []))):
                if expressionprefix != None and filename.startswith(expressionprefix):
                    expression = filename[len(expressionprefix):]
                else:
                    self.filenameexpressions.append([filename, expression])
            self.warning = self.containsUnixShellStyleWildcards and len(self.filenameexpressions) == 0
            if self.warning:
                self.message = "Your filename argument(s) contain Unix shell-style wildcards, but no files were matched.\nCheck your wildcard patterns or use option literalfilenames if you don't want wildcard pattern matching."
                return
        if self.filenameexpressions == [] and expression != '':
            self.filenameexpressions = [['', expression]]
        if checkfilenames:
            self.CheckIfFilesAreValid()

    def Glob(self, filename):
        if not ('?' in filename or '*' in filename or ('[' in filename and ']' in filename)):
            return [filename]
        self.containsUnixShellStyleWildcards = True
        return glob.glob(filename)

    def CheckIfFilesAreValid(self):
        valid = []
        doesnotexist = []
        isnotafile = []
        for filename, expression in self.filenameexpressions:
            hashfile = False
            try:
                hashfile = FilenameCheckHash(filename, self.literalfilenames)[0] == FCH_DATA
            except:
                pass
            if filename == '' or hashfile:
                valid.append([filename, expression])
            elif not os.path.exists(filename):
                doesnotexist.append(filename)
            elif not os.path.isfile(filename):
                isnotafile.append(filename)
            else:
                valid.append([filename, expression])
        self.filenameexpressions = valid
        if len(doesnotexist) > 0:
            self.warning = True
            self.message += 'The following files do not exist and will be skipped: ' + ' '.join(doesnotexist) + '\n'
        if len(isnotafile) > 0:
            self.warning = True
            self.message += 'The following files are not regular files and will be skipped: ' + ' '.join(isnotafile) + '\n'

    def Filenames(self):
        if self.expressionprefix == None:
            return [filename for filename, expression in self.filenameexpressions]
        else:
            return self.filenameexpressions