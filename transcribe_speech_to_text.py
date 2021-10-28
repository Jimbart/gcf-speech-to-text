
import argparse
import io, os.path

# [START transcribe_gcs]
def transcribe_speech_to_text(data, context):
    """Transcribes the audio file specified by the gcs_uri."""

# Beta PAckages    
#    from google.cloud import speech_v1p1beta1 as speech
#    from google.cloud.speech_v1p1beta1 import enums
#    from google.cloud.speech_v1p1beta1 import types

    from google.cloud import speech_v1 as speech
    from google.cloud.speech_v1 import enums
    from google.cloud.speech_v1 import types
    
    from google.cloud import storage, exceptions
    from google.cloud import pubsub_v1

# Define variables for pubsub
# current project and topic name

    project_id = 'smtp-v2t-240608'
    topic_name = 'transcribed_text'

# Bucket name for deletion of file after transcription

    bucket_name = 'voice_dumps_v2t_poc'
    
# Input parameters, converting input audio to text
    
    file_name = str(data['name'])
    email_sender = str(data['metadata']['email_sender'])
    if 'email_subject' in data['metadata']:
        email_subject = str(data['metadata']['email_subject'])
    else:
        email_subject = None
    input_bucket_uri = 'gs://' + bucket_name + '/'
    gcs_uri = input_bucket_uri + file_name
    
# [START speech to text transcription]
    client = speech.SpeechClient()   
    audio = types.RecognitionAudio(uri=gcs_uri)

# Get first 3 characters in email label to identify region
# adjust encoding depending on the region. 
    if email_sender[:3] in ['418','438','450','514','579','581','819','873','506']:
        config = types.RecognitionConfig(
            language_code='fr-FR')
# Beta version
#            language_code='en_US',
#            alternative_language_codes=['fr-FR','zh'],
#            enable_automatic_punctuation=True)       
    else:
        config = types.RecognitionConfig(
            language_code='en_US')
# Beta version
#            language_code='en_US',
#            alternative_language_codes=['fr-FR','zh'],
#            enable_automatic_punctuation=True)        

# Check if file extension is supported, skip unsupported file types
# We do this to avoid unnecessary runtime seconds on cloud function. (save $)
    filename, file_ext = os.path.splitext(file_name)
    if file_ext.lower() in ('.wav', '.flac'):
        try:
            operation = client.long_running_recognize(config, audio)
            response = operation.result(timeout=300)
# Each result is for a consecutive portion of the audio. Iterate through
# them to get the transcripts for the entire audio file.
# Create string variable to contain all transcripts
            transcribed_text = ""
            for result in response.results:
                print(f"Transcript: {result.alternatives[0].transcript}")
                print(f"Confidence: {result.alternatives[0].confidence}")
                transcribed_text = transcribed_text + result.alternatives[0].transcript
        except:
            transcribed_text = 'Unable to Recognize Audio Format.'
    else:
        transcribed_text = 'Unsupported Audio Format.'

# [START Delete object after transcription]
    try:
        storage_client = storage.Client()
        bucket = storage_client.get_bucket(bucket_name)
        blob = bucket.blob(file_name)
        blob.delete()
        print(f"Deleted audio attachment: {file_name}")    
    except exceptions.NotFound:
        print(f"Bucket object not found: {bucket_name}/{file_name}")        
        
# [START PUBSUB Message Creation]

    publisher = pubsub_v1.PublisherClient()
    project_path = publisher.project_path(project_id)
    topic_path = publisher.topic_path(project_id, topic_name)

    data = transcribed_text
# Data must be a bytestring
    data = data.encode('utf-8')
# Add one attribute, key:value, email_sender_metadata:email_sender
# Where email_sender_metadata is the key name, and email_sender is the value/variable taken from bucket object metadata
    if email_subject is None:
        publisher.publish(topic_path, data, email_sender_metadata=email_sender)
    else:
        publisher.publish(topic_path, data, email_sender_metadata=email_sender, email_subject_metadata=email_subject)
    print(f"Publishing data to PubSub topic: {topic_name}")    

# [END transcribe_v2t]