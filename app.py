from flask import Flask, render_template, Response, request
import cv2
import pickle
import numpy as np
import cvzone
import serial
import time

app = Flask(__name__)

cap = cv2.VideoCapture(0)
cap1 = cv2.VideoCapture('carPark.mp4')

with open('CarParkPos', 'rb') as f:
    posList = pickle.load(f)

width, height = 200, 100

bookedSpaces = [False] * len(posList)

def pesan_tempat_parkir(nomor_petak):
    global bookedSpaces

    if 1 <= nomor_petak <= len(bookedSpaces) and not bookedSpaces[nomor_petak - 1]:
        bookedSpaces[nomor_petak - 1] = True
        return f'Tempat parkir nomor {nomor_petak} berhasil dipesan. ' \
               f'Untuk me-reset pemesanan klik tombol reset pesanan.'
    else:
        return f'Tempat parkir nomor {nomor_petak} tidak tersedia atau sudah dipesan.'

def reset_pemesanan():
    global bookedSpaces
    bookedSpaces = [False] * len(posList)
    return 'Semua tempat parkir telah di-reset.'

def checkParkingSpace():
    global bookedSpaces

    while True:
        success, img = cap.read()
        if not success:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        imgBlur = cv2.GaussianBlur(imgGray, (3, 3), 1)
        imgThreshold = cv2.adaptiveThreshold(imgBlur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                             cv2.THRESH_BINARY_INV, 25, 16)
        imgMedian = cv2.medianBlur(imgThreshold, 5)
        kernel = np.ones((3, 3), np.uint8)
        imgDilate = cv2.dilate(imgMedian, kernel, iterations=1)

        spaceCounter = 0

        for i, pos in enumerate(posList):
            x, y = pos
            imgCrop = imgDilate[y:y + height, x:x + width]
            count = cv2.countNonZero(imgCrop)

            if not bookedSpaces[i]:
                if count < 2500:
                    color = (0, 255, 0)
                    thickness = 5
                    spaceCounter += 1
                else:
                    color = (0, 0, 255)
                    thickness = 2
            else:
                color = (0, 255, 255)
                thickness = 5
            text_offset_x = int((width - cv2.getTextSize(str(i), cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0][0]) / 2)
            text_offset_y = int((height + cv2.getTextSize(str(i), cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0][1]) / 2)
            text_position = (x + text_offset_x, y + text_offset_y)
            cv2.rectangle(img, pos, (pos[0] + width, pos[1] + height), color, thickness)
            cv2.putText(img, str(i + 1), text_position, cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        cvzone.putTextRect(img, f'Tersedia: {spaceCounter}/{len(posList)}', (100, 50), scale=3,
                          thickness=5, offset=20, colorR=(0, 200, 0))

        ret, buffer = cv2.imencode('.jpg', img)
        frame = buffer.tobytes()
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        
def checkParkingSpace1():
    global bookedSpaces

    with open('CarParkPos1', 'rb') as f:
        posList = pickle.load(f)

    width, height = 107, 48

    while True:
        success, img = cap1.read()
        if not success:
            cap1.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        imgBlur = cv2.GaussianBlur(imgGray, (3, 3), 1)
        imgThreshold = cv2.adaptiveThreshold(imgBlur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                             cv2.THRESH_BINARY_INV, 25, 16)
        imgMedian = cv2.medianBlur(imgThreshold, 5)
        kernel = np.ones((3, 3), np.uint8)
        imgDilate = cv2.dilate(imgMedian, kernel, iterations=1)

        spaceCounter = 0
        for pos in posList:
            x, y = pos
            imgCrop = imgDilate[y:y + height, x:x + width]
            count = cv2.countNonZero(imgCrop)
            if count < 900:
                color = (0, 255, 0)
                thickness = 5
                spaceCounter += 1
            else:
                color = (0, 0, 255)
                thickness = 2
            cv2.rectangle(img, pos, (pos[0] + width, pos[1] + height), color, thickness)
            cvzone.putTextRect(img, str(count), (x, y + height - 3), scale=1, thickness=2, offset=0, colorR=color)

        cvzone.putTextRect(img, f'Free: {spaceCounter}/{len(posList)}', (100, 50), scale=3, thickness=5, offset=20, colorR=(0, 200, 0))

        ret, buffer = cv2.imencode('.jpg', img)
        frame = buffer.tobytes()
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template('base.html')

@app.route('/video_feed')
def video_feed():
    return Response(checkParkingSpace(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/video_feed1')
def video_feed1():
    return Response(checkParkingSpace1(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/pesan_parkir', methods=['POST'])
def pesan_parkir():
    nomor_petak = int(request.form['nomor_petak'])
    pesan = pesan_tempat_parkir(nomor_petak)
    return render_template('base.html', pesan=pesan)

@app.route('/reset_parking')
def reset_parking():
    global bookedSpaces
    bookedSpaces = [False] * len(posList)
    pesan = 'Semua tempat parkir telah di-reset.'
    return render_template('base.html', posList=posList, pesan=pesan)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
