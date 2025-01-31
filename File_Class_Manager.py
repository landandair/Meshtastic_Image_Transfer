import os.path
import random
import file_classes
from Packaging_Data import decode_initial_req


class FileTransManager:
    def __init__(self, interface, send_delay=7, packet_len=200, destination=None, auto_restart=False):
        self.transfer_objects = {}  # id: file_sender/file_receiver
        self.interface = interface
        self.send_delay = send_delay
        self.packet_len = packet_len
        self.file_list = []
        self.destination = destination
        self.done = False
        self.restart = auto_restart

    def update_all(self):
        """Calls update method on each object"""
        deleted_keys = []
        for key in self.transfer_objects.keys():
            self.transfer_objects[key].update()
            if self.transfer_objects[key].kill:
                deleted_keys.append(key)

        for key in deleted_keys:
            finished = self.transfer_objects.pop(key)
            if not finished.finished:
                if not self.restart:
                    result = input('retry?(y/n)>>')
                else:
                    result = ""
                if 'y' in result.lower() or self.restart:
                    print('restarting ', finished.name)
                    self.file_list.insert(0, finished.name)

        if len(self.transfer_objects) == 0:
            if self.file_list:
                file = self.file_list.pop(0)
                if os.path.exists(file) and self.destination:
                    self.send_new_file(file, self.destination)
            else:
                self.done = True

    def new_data_packet(self, packet):
        """Called to process new data packet"""
        if packet[0] == bytearray('f'.encode('utf8'))[0] and packet[4] in self.transfer_objects:
            # print(f'com packet: {packet}')
            f_id = packet[4]
            self.transfer_objects[f_id].manage_com_packet(packet)
        elif packet[0] in self.transfer_objects.keys():
            # print(f'file packet received for {int(packet[0])}: {packet}')
            self.transfer_objects[packet[0]].add_packet(packet)
        else:
            print(f'something went Wrong: {packet}')

    def new_req_packet(self, initial_req, sending_id, timeout=100):
        """Called to make new file_receiving packet based on a request packet"""
        file_name, f_id, num = decode_initial_req(initial_req)
        if self.restart:
            print(f'Automatically Accepted {file_name} with a size of {round(num*self.packet_len / 1000, 2)}kb.')
        elif 'y' in input(f'Receive {file_name} with an approx size of {round(num*self.packet_len/1000,2)}kb?(y/n)\n>>'):
            print('Accepted')
        else:
            return
        self.transfer_objects[f_id] = file_classes.FileTransferReceiver(file_name, f_id, num, self.interface,
                                                                        sending_id, timeout=timeout)

    def send_new_file(self, file_name, destination):
        """Called to make new file sending object"""
        file_id = random.randint(0, 256)
        while file_id == bytearray('f'.encode('utf8'))[0] or file_id in self.transfer_objects.keys():
            file_id = random.randint(0, 256)
        print(f'Sending {file_name}...')
        self.transfer_objects[file_id] = file_classes.FileTransferSender(file_name, file_id, self.interface,
                                                                         destination, self.send_delay, self.packet_len,
                                                                         disable_bar=False)

    def send_new_files(self, file_names: list, destination=None):
        """Called to make new file sending object"""
        if destination:
            self.destination = destination
        for file in sorted(file_names):
            self.file_list.append(file)
