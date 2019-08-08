using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Threading.Tasks;
using Amazon;
using Amazon.Lambda.Core;
using Amazon.Lambda.SQSEvents;
using Amazon.S3;
using Amazon.S3.Transfer;
using Newtonsoft.Json;
using PDFSanitizer.Services;


// Assembly attribute to enable the Lambda function's JSON input to be converted into a .NET class.
[assembly: LambdaSerializer(typeof(Amazon.Lambda.Serialization.Json.JsonSerializer))]

namespace PDFSanitizer
{
    public class Function
    {
        private readonly PDFSanitizerService _pdfSanitizerService= new PDFSanitizerService("/tmp/rawFiles", "/tmp/convertedFiles");
       // private static IAmazonS3 _s3Client;
      //  private static readonly RegionEndpoint bucketRegion = RegionEndpoint.USEast1; 

        /// <summary>
        /// Default constructor. This constructor is used by Lambda to construct the instance. When invoked in a Lambda environment
        /// the AWS credentials will come from the IAM role associated with the function and the AWS region will be set to the
        /// region the Lambda function is executed in.
        /// </summary>
        public Function()
        {
            // _s3Client = new AmazonS3Client(bucketRegion);
        }


        /// <summary>
        /// This method is called for every Lambda invocation. This method takes in an SQS event object and can be used 
        /// to respond to SQS messages.
        /// </summary>
        /// <param name="evnt"></param>
        /// <param name="context"></param>
        /// <returns></returns>
        public async Task FunctionHandler(SQSEvent evnt, ILambdaContext context)
        {
            foreach(var message in evnt.Records)
            {
                await ProcessMessageAsync(message, context);
            }
        }

        private async Task ProcessMessageAsync(SQSEvent.SQSMessage message, ILambdaContext context)
        {
            await Task.CompletedTask;
            context.Logger.LogLine($"Received message {message.Body}");
            SanitizePdfRequest request = JsonConvert.DeserializeObject<SanitizePdfRequest>(message.Body);
            string outputLocation = _pdfSanitizerService.SanitizePdf(request.FileUrl);
            UploadToS3(request.ConvertedPutUrl, outputLocation);
            File.Delete(outputLocation);
            context.Logger.LogLine($"Processed message for file: {request.FileName}");
        }

        private bool UploadToS3( string fileDestinationUrl, string fileLocation)
        {
            try
            {
                using (var webClient = new WebClient())
                {
                    webClient.UploadFileAsync(new Uri(fileDestinationUrl), fileLocation);
                }

                return true;
            }
            catch(Exception e)
            {
                Console.Write($"Something went wrong while uploading the file to the PutUrl. File destination {fileDestinationUrl} " +
                              $"Exception Message: {e.Message} " +
                              $"StackTrace: {e.StackTrace} ");
            }
            
            return false;
        }
    }

    internal class SanitizePdfRequest
    {
        public string ConvertedPutUrl;
        public string FileName;
        public string FileUrl;
    }
}
