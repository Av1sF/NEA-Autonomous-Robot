import glob
import os

print(os.getcwd())
folder_path = r"{}/train_files".format(os.getcwd())
print(folder_path)
file_type = r'/*csv'
print("done")
files = glob.glob("/home/pi/Desktop/rewriteNEArobotwebsite/train_files" + file_type)
print(files)
max_file = max(files, key=os.path.getctime)
print(max_file.split('/')[-1])
