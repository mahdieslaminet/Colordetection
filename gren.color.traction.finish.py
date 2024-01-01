import cv2
import requests
import numpy as np
import time
import traceback
import serial  # Change the import statement
from serial import Serial, SerialException

serial_port = 'COM5'  # Change this to your Arduino's serial port
baud_rate = 9600

url = 'http://192.168.41.25/capture'

arduino = None

# Set up initial tracking parameters
# Define the lower and upper bounds for orange color in HSV
green_lower = np.array([40, 40, 40])
green_upper = np.array([50, 255, 255])
# Create a list to store the tracked points
points = []

try:
    arduino = Serial(serial_port, baud_rate, timeout=1)
except SerialException as e:
    print(f"Serial Exception: {e}")
    exit()
except Exception as e:
    print(f"Error: {e}")
    exit()

flag = 0
no_face_time = 0.0

while True:
    try:
        # Get image from URL
        response = requests.get(url)
        img_array = np.array(bytearray(response.content), dtype=np.uint8)
        img = cv2.imdecode(img_array, -1)
        
        # Decode image
        frame = cv2.imdecode(img_array, -1)

        # Convert BGR to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Threshold the HSV image to get only green colors
        mask = cv2.inRange(hsv, green_lower, green_upper)

        # Perform dilation and erosion to remove noise
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)

        frame_height, frame_width, _ = img.shape

        center_square = [(frame_width // 2 - 20, frame_height //2 - 20),
                 (frame_width // 2 + 20, frame_height // 2 + 20)]

        # Find contours in the mask
        contours, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        cv2.rectangle(frame, center_square[0], center_square[1], (255, 0, 0), 2)

        # Reset the ball position (center) for each iteration
        center = None

        if len(contours) > 0:
            # Find the largest contour
            c = max(contours, key=cv2.contourArea)
            ((x, y), radius) = cv2.minEnclosingCircle(c)

            # Calculate moments for center
            M = cv2.moments(c)
            if M["m00"] != 0:
                center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))

                # Draw the circle and centroid on the frame
                cv2.circle(frame, (int(x), int(y)), int(radius), (0, 255, 255), 2)
                cv2.circle(frame, center, 5, (0, 0, 255), -1)


            if center is not None and center_square[0][0] < center[0] < center_square[1][0] \
                        and center_square[0][1] < center[1] < center_square[1][1]:
                    pass
            else:
                if flag == 0:
                     no_face_time = time.time()#no face detected = record time
                     flag = 1

                if y < frame_height / 2 + 0.5:
                        arduino.write(b'u')  # Move tilt up
                elif y > frame_height / 2 + 0.5:
                        arduino.write(b'd')  # Move tilt down

                if x < frame_width / 2 + 0.5:
                        arduino.write(b'l')  # Move pan left
                elif x > frame_width / 2 + 0.5:
                        arduino.write(b'r')  # Move pan right

        else:
            if time.time() - no_face_time >= 5:  # Check if 2 seconds have passed
                arduino.write(b's')  # Move to default position
                print("No face detected.")
                flag = 0  # Reset flag
                no_face_time = 0.0  # Reset no_face_time
            
        # Add the center to the list of tracked points
        points.append(center)

        # Display the frame
        cv2.imshow("Frame", frame)

        # Break the loop on 'q' press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    except Exception as e:
        print(f"Error occurred: {e}")
if arduino:
    arduino.close()
cv2.destroyAllWindows()