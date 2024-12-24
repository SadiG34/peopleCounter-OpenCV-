import os
from tracker.centroidtracker import CentroidTracker
from tracker.trackableobject import TrackableObject
from imutils.video import VideoStream
from itertools import zip_longest
from utils.mailer import Mailer
from imutils.video import FPS
from utils import thread
from tkinter import simpledialog, messagebox, Listbox, Scrollbar, Menu
from google.oauth2.service_account import Credentials
import threading
import numpy as np
import gspread
import threading
import argparse
import datetime
import schedule
import logging
import imutils
import argparse
import time
import dlib
import json
import csv
import cv2
import tkinter as tk


# execution start time
start_time = time.time()
# setup logger


logging.basicConfig(level = logging.INFO, format = "[INFO] %(message)s")
logger = logging.getLogger(__name__)
# initiate features config.
with open("utils/config.json", "r") as file:
    config = json.load(file)

# Определяем области доступа
scopes = [
    "https://spreadsheets.google.com/feeds",
    'https://www.googleapis.com/auth/spreadsheets',
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

# Загружаем учетные данные



def parse_arguments():
	# функция для разбора аргументов
	ap = argparse.ArgumentParser()
	ap.add_argument("-p", "--prototxt", required=False, default='detector/MobileNetSSD_deploy.prototxt',
					help="path to Caffe 'deploy' prototxt file")
	ap.add_argument("-m", "--model", required=False, default='detector/MobileNetSSD_deploy.caffemodel',
					help="path to Caffe pre-trained model")
	ap.add_argument("-i", "--input", type=str,
					help="path to optional input video file")
	ap.add_argument("-o", "--output", type=str,
					help="path to optional output video file")
	# confidence default 0.4
	ap.add_argument("-c", "--confidence", type=float, default=0.4,
					help="minimum probability to filter weak detections")
	ap.add_argument("-s", "--skip-frames", type=int, default=30,
					help="# of skip frames between detections")

	args = vars(ap.parse_args())
	return args




def send_mail():
	# function to send the email alerts
	Mailer().send(config["Email_Receive"])

def log_data(move_in, in_time, move_out, out_time):
	# function to log the counting data
	data = [move_in, in_time, move_out, out_time]
	# transpose the data to align the columns properly
	export_data = zip_longest(*data, fillvalue = '')

	with open('utils/data/logs/counting_data.csv', 'w', newline = '') as myfile:
		wr = csv.writer(myfile, quoting = csv.QUOTE_ALL)
		if myfile.tell() == 0: # check if header rows are already existing
			wr.writerow(("Move In", "In Time", "Move Out", "Out Time"))
			wr.writerows(export_data)

URLS_FILE = "urls.json"

class App:
	def __init__(self, master):
		self.master = master
		self.master.title("People Counter App")
		self.master.geometry("400x400")

		self.add_url_button = tk.Button(master, text="Добавить URL", command=self.get_url)
		self.add_url_button.pack(pady=10)

		self.delete_url_button = tk.Button(master, text="Удалить URL", command=self.delete_url)
		self.delete_url_button.pack(pady=10)

		self.exit_button = tk.Button(master, text="Выход", command=master.quit)
		self.exit_button.pack(pady=10)

		self.url_list = Listbox(master, width=50)
		self.url_list.pack(pady=10)

		self.scrollbar = Scrollbar(master)
		self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
		self.url_list.config(yscrollcommand=self.scrollbar.set)
		self.scrollbar.config(command=self.url_list.yview)

		self.start_button = tk.Button(master, text="Запустить камеру", command=self.start_camera)
		self.start_button.pack(pady=10)

		self.load_urls()

		# Настраиваем контекстное меню
		self.menu = Menu(master, tearoff=0)
		self.menu.add_command(label="Свойства", command=self.show_properties)

		self.url_list.bind("<Button-3>", self.show_context_menu)

	def show_context_menu(self, event):
		"""Показать контекстное меню при нажатии правой кнопки мыши."""
		self.url_list.selection_clear(0, tk.END)  # Отменяем выделение
		self.url_list.activate(self.url_list.nearest(event.y))  # Активируем элемент по положению курсора
		self.url_list.selection_set(self.url_list.nearest(event.y))  # Выделяем элемент
		self.menu.post(event.x_root, event.y_root)  # Позиционируем меню по координатам курсора

	def show_properties(self):
		"""Показать свойства выбранного URL."""
		selected_index = self.url_list.curselection()
		if not selected_index:
			messagebox.showwarning("Предупреждение", "Пожалуйста, выберите URL из списка.")
			return

		entry_string = self.url_list.get(selected_index)
		# Предполагается, что строка выглядит как "url - location"
		url, location = entry_string.split(" - ")

		# Создаем строку для отображения
		properties = f"URL: {url}\nЛокация: {location}\nДата/время: {self.get_current_datetime()}"
		messagebox.showinfo("Свойства", properties)

	def get_current_datetime(self):
		"""Возвращает текущую дату и время в строковом формате."""
		from datetime import datetime
		return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

	def get_url(self):
		root = tk.Tk()
		root.withdraw()  # Скрыть основное окно
		url = simpledialog.askstring("Input", "Введите URL:", parent=root)
		if url:
			# Запрос локации
			location = simpledialog.askstring("Input", "Введите место:", parent=root)

			# Формирование строки с URL и локацией
			if location:
				entry_string = f"{url} - {location}"
				self.url_list.insert(tk.END, entry_string)  # Добавить URL и локацию в список
				logger.info(f"Добавлен URL: {url}, Локация: {location}")
				self.save_urls()  # Сохраняем URL в файл



	def delete_url(self):
		selected_index = self.url_list.curselection()
		if not selected_index:
			messagebox.showwarning("Предупреждение", "Пожалуйста, выберите URL из списка для удаления.")
			return

		# Удаляем выбранный URL и сохраняем изменения
		url = self.url_list.get(selected_index)
		self.url_list.delete(selected_index)
		logger.info(f"Удален URL: {url}")
		self.save_urls()  # Сохраняем изменения

	def start_camera(self):
		selected_index = self.url_list.curselection()
		if not selected_index:
			messagebox.showwarning("Предупреждение", "Пожалуйста, выберите URL из списка.")
			return

		url = self.url_list.get(selected_index)
		logger.info(f"Подключение к камере: {url}")

		# Запускаем people_counter в отдельном потоке
		threading.Thread(target=self.people_counter, args=(url,), daemon=True).start()


	def save_urls(self):
		"""Сохраняем список URL в файл JSON."""
		urls = self.url_list.get(0, tk.END)  # Получаем все URL из списка
		with open(URLS_FILE, "w") as file:
			json.dump(list(urls), file)  # Сохраняем как JSON

	def load_urls(self):
		"""Загружаем список URL из файла JSON."""
		if os.path.exists(URLS_FILE):
			with open(URLS_FILE, "r") as file:
				content = file.read()
				if content:  # Проверяем, что файл не пуст
					urls = json.loads(content)
					for url in urls:  # Добавляем URL в список
						self.url_list.insert(tk.END, url)
					logger.info("Загружены URL из файла: " + str(urls))
				else:
					logger.info("Файл urls.json пуст. Начинаем с пустого списка.")
		else:
			logger.info("Файл urls.json не найден. Создаётся новый файл.")
			# Создать файл с пустым массивом
			with open(URLS_FILE, "w") as file:
				file.write("[]")  # Это создаст пустой JSON массив

	def people_counter(self, url):
		args = parse_arguments()
		# initialize the list of class labels MobileNet SSD was trained to detect
		CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat",
				   "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
				   "dog", "horse", "motorbike", "person", "pottedplant", "sheep",
				   "sofa", "train", "tvmonitor"]

		# load our serialized model from disk
		net = cv2.dnn.readNetFromCaffe(args["prototxt"], args["model"])

		# if a video path was not supplied, grab a reference to the ip camera
		if not args.get("input", False):
			logger.info("Starting the live stream..")
			vs = VideoStream(url).start()
			time.sleep(2.0)

		# otherwise, grab a reference to the video file
		else:
			logger.info("Starting the video..")
			vs = cv2.VideoCapture(args["input"])

		# initialize the video writer (we'll instantiate later if need be)
		writer = None

		# initialize the frame dimensions (we'll set them as soon as we read
		# the first frame from the video)
		W = None
		H = None

		# instantiate our centroid tracker, then initialize a list to store
		# each of our dlib correlation trackers, followed by a dictionary to
		# map each unique object ID to a TrackableObject
		ct = CentroidTracker(maxDisappeared=40, maxDistance=50)
		trackers = []
		trackableObjects = {}

		# initialize the total number of frames processed thus far, along
		# with the total number of objects that have moved either up or down
		totalFrames = 0
		totalDown = 0
		totalUp = 0
		# initialize empty lists to store the counting data
		total = []
		move_out = []
		move_in = []
		out_time = []
		in_time = []

		# start the frames per second throughput estimator
		fps = FPS().start()

		if config["Thread"]:
			vs = thread.ThreadingClass(url)

		# loop over frames from the video stream
		while True:
			# grab the next frame and handle if we are reading from either
			# VideoCapture or VideoStream
			frame = vs.read()
			frame = frame[1] if args.get("input", False) else frame

			# if we are viewing a video and we did not grab a frame then we
			# have reached the end of the video
			if args["input"] is not None and frame is None:
				break

			# resize the frame to have a maximum width of 500 pixels (the
			# less data we have, the faster we can process it), then convert
			# the frame from BGR to RGB for dlib
			frame = imutils.resize(frame, width=500)
			rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

			# if the frame dimensions are empty, set them
			if W is None or H is None:
				(H, W) = frame.shape[:2]

			if W is None:
				W = frame.shape[1]
			if H is None:
				H = frame.shape[0]

			# if we are supposed to be writing a video to disk, initialize
			# the writer
			if args["output"] is not None and writer is None:
				fourcc = cv2.VideoWriter_fourcc(*"mp4v")
				writer = cv2.VideoWriter(args["output"], fourcc, 30,
										 (W, H), True)

			# initialize the current status along with our list of bounding
			# box rectangles returned by either (1) our object detector or
			# (2) the correlation trackers
			status = "Waiting"
			rects = []

			# check to see if we should run a more computationally expensive
			# object detection method to aid our tracker
			if totalFrames % args["skip_frames"] == 0:
				# set the status and initialize our new set of object trackers
				status = "Detecting"
				trackers = []

				# convert the frame to a blob and pass the blob through the
				# network and obtain the detections
				blob = cv2.dnn.blobFromImage(frame, 0.007843, (W, H), 127.5)
				net.setInput(blob)
				detections = net.forward()

				# loop over the detections
				for i in np.arange(0, detections.shape[2]):
					# извлечь достоверность (т. е. вероятность), связанную
					# с предсказанием
					confidence = detections[0, 0, i, 2]

					# отфильтровывать слабые обнаружения, требуя минимального
					# уверенность
					if confidence > args["confidence"]:
						# извлеките индекс метки класса из
						# список обнаружений
						idx = int(detections[0, 0, i, 1])

						# если метка класса не является человеком, игнорировать ее
						if CLASSES[idx] != "person":
							continue

						# вычисляем координаты (x, y) ограничивающего прямоугольника
						# для объекта
						box = detections[0, 0, i, 3:7] * np.array([W, H, W, H])
						(startX, startY, endX, endY) = box.astype("int")

						# создаем объект прямоугольника dlib по границе
						# координаты поля, а затем начать корреляцию dlib
						# трекер
						tracker = dlib.correlation_tracker()
						rect = dlib.rectangle(startX, startY, endX, endY)
						tracker.start_track(rgb, rect)

						# добавьте трекер в наш список трекеров, чтобы мы могли
						# использовать его во время пропуска кадров
						trackers.append(tracker)

			# в противном случае нам следует использовать *трекеры* наших объектов, а не
			# *детекторы* объектов для повышения производительности обработки кадров
			else:
				# перебирать трекеры
				for tracker in trackers:
					# вместо этого установите статус нашей системы на «отслеживание»
					# чем «ожидание» или «обнаружение»
					status = "Tracking"

					# обновляем трекер и фиксируем обновленную позицию
					tracker.update(rgb)
					pos = tracker.get_position()

					# распаковать объект позиции
					startX = int(pos.left())
					startY = int(pos.top())
					endX = int(pos.right())
					endY = int(pos.bottom())

					# добавить координаты ограничивающего прямоугольника в список прямоугольников
					rects.append((startX, startY, endX, endY))

			# рисуем горизонтальную линию в центре кадра - один раз
			# объект пересекает эту линию, мы определим, были ли они
			# перемещение «вверх» или «вниз»
			cv2.line(frame, (0, H // 2), (W, H // 2), (0, 0, 0), 3)
			cv2.putText(frame, "-Prediction border - Entrance-", (10, H - ((i * 20) + 200)),
						cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

			# используйте трекер центроидов, чтобы связать (1) старый объект
			# центроидов с (2) вновь вычисленными центроидами объекта
			objects = ct.update(rects)

			# цикл по отслеживаемым объектам
			for (objectID, centroid) in objects.items():
				import datetime

				def log_info(exit_count, enter_count, total_people, status, location):
					date_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

					# Загружаем учетные данные
					creds = Credentials.from_service_account_file('credentials.json', scopes=scopes)
					client = gspread.authorize(creds)

					# Открываем таблицу по ID
					sheet_id = ''
					spreadsheet = client.open_by_key(sheet_id)

					# Проверяем, существует ли вкладка с названием местоположения
					try:
						worksheet = spreadsheet.worksheet(location)  # Проверяем существование листа
					except gspread.WorksheetNotFound:
						# Если вкладка не найдена, создаем новую
						worksheet = spreadsheet.add_worksheet(title=location, rows="100",
															  cols="5")  # Указываем размеры по мере необходимости

					# Записываем данные в новую строку
					worksheet.append_row([date_time, exit_count, enter_count, total_people, status])

				# проверяем, существует ли отслеживаемый объект для текущего object ID
				# идентификатор объекта
				to = trackableObjects.get(objectID, None)

				# если существующего отслеживаемого объекта нет, создайте его
				if to is None:
					to = TrackableObject(objectID, centroid)

				# в противном случае есть отслеживаемый объект, и мы можем его использовать
				# для определения направления
				else:
					# разница между координатой y *текущего*
					# центроид и среднее значение *предыдущих* центроидов покажут
					# нам, в каком направлении движется объект (отрицательное значение для
					# 'вверх' и положительный для 'вниз')
					y = [c[1] for c in to.centroids]
					direction = centroid[1] - np.mean(y)
					to.centroids.append(centroid)

					# проверяем, засчитан объект или нет
					if not to.counted:
						# если направление отрицательное (с указанием объекта
						# движется вверх) И центр тяжести находится над центром
						# строка, посчитать объект
						if direction < 0 and centroid[1] < H // 2:
							totalUp += 1
							selected_index = self.url_list.curselection()
							entry_string = self.url_list.get(selected_index)
							# Предполагается, что строка выглядит как "url - location"
							url, location = entry_string.split(" - ")
							log_info(totalUp, totalDown, ', '.join(map(str, total)), status, location)
							date_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
							move_out.append(totalUp)
							out_time.append(date_time)
							to.counted = True


						# если направление положительное (указывает на объект
						# движется вниз) И центр тяжести находится ниже
						# центральная линия, посчитайте объект

						elif direction > 0 and centroid[1] > H // 2:
							totalDown += 1
							date_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
							move_in.append(totalDown)
							in_time.append(date_time)
							selected_index = self.url_list.curselection()
							entry_string = self.url_list.get(selected_index)
							# Предполагается, что строка выглядит как "url - location"
							url, location = entry_string.split(" - ")
							log_info(totalUp, totalDown, ', '.join(map(str, total)), status, location)

							# если лимит людей превышает порог, отправьте оповещение по электронной почте
							if sum(total) >= config["Threshold"]:
								cv2.putText(frame, "-ALERT: People limit exceeded-", (10, frame.shape[0] - 80),
											cv2.FONT_HERSHEY_COMPLEX, 0.5, (0, 0, 255), 2)
								if config["ALERT"]:
									logger.info("Sending email alert..")
									email_thread = threading.Thread(target=send_mail)
									email_thread.daemon = True
									email_thread.start()
									logger.info("Alert sent!")
							to.counted = True
							# вычислить общее количество людей внутри
							total = []
							total.append(len(move_in) - len(move_out))

				# сохраняем отслеживаемый объект в нашем словаре
				trackableObjects[objectID] = to

				#  нарисуйте идентификатор объекта и центр тяжести
				# объект в выходном кадре
				text = "ID {}".format(objectID)
				cv2.putText(frame, text, (centroid[0] - 10, centroid[1] - 10),
							cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
				cv2.circle(frame, (centroid[0], centroid[1]), 4, (255, 255, 255), -1)

			# создаем кортеж информации, которую мы будем отображать в кадре
			info_status = [
				("Exit", totalUp),
				("Enter", totalDown),
				("Status", status),
			]

			info_total = [
				("Total people inside", ', '.join(map(str, total))),
			]

			# отображаем вывод
			for (i, (k, v)) in enumerate(info_status):
				text = "{}: {}".format(k, v)
				cv2.putText(frame, text, (10, H - ((i * 20) + 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

			for (i, (k, v)) in enumerate(info_total):
				text = "{}: {}".format(k, v)
				cv2.putText(frame, text, (265, H - ((i * 20) + 60)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

			# запускаем простой журнал для сохранения данных подсчета
			if config["Log"]:
				selected_index = self.url_list.curselection()
				entry_string = self.url_list.get(selected_index)
				# Предполагается, что строка выглядит как "url - location"
				url, location = entry_string.split(" - ")
				log_info(move_in, in_time, move_out, out_time, location)

			# check to see if we should write the frame to disk
			if writer is not None:
				writer.write(frame)

			# show the output frame
			cv2.imshow("Real-Time Monitoring/Analysis Window", frame)
			key = cv2.waitKey(10) & 0xFF
			# if the `q` key was pressed, break from the loop
			if cv2.getWindowProperty("Real-Time Monitoring/Analysis Window", cv2.WND_PROP_VISIBLE) < 1:
				break

			if key == ord("q"):
				break
			# increment the total number of frames processed thus far and
			# then update the FPS counter
			totalFrames += 1
			fps.update()

			# initiate the timer
			if config["Timer"]:
				# automatic timer to stop the live stream (set to 8 hours/28800s)
				end_time = time.time()
				num_seconds = (end_time - start_time)
				if num_seconds > 28800:
					break

			# stop the timer and display FPS information


			# release the camera device/resource (issue 15)
			if config["Thread"]:
				vs.release()

		# close any open windows
		cv2.destroyAllWindows()


	# initiate the scheduler



if __name__ == "__main__":
	root = tk.Tk()
	app = App(root)
	root.mainloop()



