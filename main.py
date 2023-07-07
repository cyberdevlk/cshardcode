import cv2
import subprocess
import os
import logging
from telegram import InputFile
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler
from queue import Queue

# Telegram bot token
BOT_TOKEN = '6369661413:AAHCaIKjAMwjmWimUu9c2uk3DkKzi_8cFE8'

# HandBrakeCLI command
HAND_BRAKE_CLI_COMMAND = 'HandBrakeCLI -i "{video_path}" -o "{output_directory}/{filename}_output.mp4" -e x264 -q 22 -B 160 --x264-preset veryfast --subtitle-burned'

# Logging configuration
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

# Create an Updater object
updater = Updater(token=BOT_TOKEN, use_context=True)
dispatcher = updater.dispatcher

# Define a command handler function for the /start command
def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text='I am alive!')

# Register the command handler
start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)

# Define a message handler function
def handle_message(update, context):
    message = update.message

    # Check if the message contains a video
    if message.video:
        video_file = message.video.get_file()
        video_path = 'video.mp4'
        video_file.download(video_path)

        # Request the user to send a subtitle file
        context.bot.send_message(chat_id=update.effective_chat.id, text='Please upload a subtitle file (.ass format) for the video.')

        # Store the video path in the user data for future reference
        context.user_data['video_path'] = video_path

    # Check if the message contains a subtitle document
    if message.document and message.document.file_name.endswith('.ass'):
        subtitle_file = message.document.get_file()
        subtitle_path = f'subtitle_{update.effective_chat.id}.ass'
        subtitle_file.download(subtitle_path)

        # Check if the user previously sent a video
        if 'video_path' in context.user_data:
            # Get the video path from the user data
            video_path = context.user_data['video_path']

            # Run HandBrakeCLI command
            output_directory = 'output_directory'
            filename = os.path.splitext(os.path.basename(video_path))[0]
            command = HAND_BRAKE_CLI_COMMAND.format(video_path=video_path, output_directory=output_directory, filename=filename)
            subprocess.run(command, shell=True)

            # Open the processed video using OpenCV
            cap = cv2.VideoCapture(os.path.join(output_directory, f'{filename}_output.mp4'))

            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # Define the subtitle text and position
            subtitle_text = 'Your subtitle text here'
            subtitle_position = (50, 50)  # Adjust the position as needed

            # Define the log file path
            log_file_path = f'processing_log_{update.effective_chat.id}.txt'
            logging.basicConfig(filename=log_file_path, level=logging.INFO)

            # Loop through the frames and add subtitles
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                # Add the subtitle text to the frame
                cv2.putText(frame, subtitle_text, subtitle_position, cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                # Display the frame (optional)
                cv2.imshow('Subtitle Video', frame)
                if cv2.waitKey(int(1000/fps)) & 0xFF == ord('q'):
                    break

                # Log the processing progress
                logging.info(f'Frame processed: {cap.get(cv2.CAP_PROP_POS_FRAMES)} / {cap.get(cv2.CAP_PROP_FRAME_COUNT)}')

            # Release resources
            cap.release()
            cv2.destroyAllWindows()

            # Save the output video file
            output_video_path = os.path.join(output_directory, f'{filename}_output.mp4')
            output_video_file = open(output_video_path, 'rb')

            # Send the output video file as a Telegram document
            context.bot.send_document(chat_id=update.effective_chat.id, document=InputFile(output_video_file, filename=f'{filename}_output.mp4'))

            # Send the processing log file
            log_file = open(log_file_path, 'rb')
            context.bot.send_document(chat_id=update.effective_chat.id, document=InputFile(log_file, filename=f'processing_log.txt'))

            # Notify the user about the completion of the process
            context.bot.send_message(chat_id=update.effective_chat.id, text='Hardcoding completed!')

# Register the message handler
message_handler = MessageHandler(Filters.all, handle_message)
dispatcher.add_handler(message_handler)

# Start the bot
updater.start_polling()
