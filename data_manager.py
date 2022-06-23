import hashlib
import json


class _DataManager:
    data_file_path = None

    def __init__(self) -> None:
        self.data = self.read_json()

    # Returns dict with data from json file
    def read_json(self) -> dict:
        with open(self.data_file_path) as readFile:
            dataFromJson = json.load(readFile)
        return dataFromJson

    # Writing information to a file
    def write_json(self):
        with open(self.data_file_path, 'w') as writeFile:
            json.dump(self.data, writeFile, indent=4, sort_keys=True, ensure_ascii=False)


class ProjectsDataManager(_DataManager):
    data_file_path = "projects_data.json"

    # Updating information
    def update_json(self, project, task="", name="", times=None):
        if times is None:
            times = {}
        self.data = self.read_json()
        name = name.lower()
        if project not in self.data:
            self.data[project] = {}
        if task != "" and task not in self.data[project]:
            self.data[project][task] = {}
        if name != "" and name not in self.data[project][task]:
            self.data[project][task][name] = {}
        if times != {}:
            self.data[project][task][name] = times
        self.write_json()


class UsersDataManager(_DataManager):
    data_file_path = "users_data.json"

    # Updating information
    def update_json(self, user_id, attribute, value):
        user_id = str(user_id)
        if user_id not in self.data:
            self.data[user_id] = {}

        self.data[user_id][attribute] = value

        self.write_json()


class CallbackDataManager(_DataManager):
    """Handles Telegram's 64-bit limit for callback query"""

    data_file_path = "callback_hash.json"

    def get_hash_by_data(self, callback_data):
        hash_ = hashlib.md5(callback_data.encode('utf-8')).hexdigest()
        self.data[hash_] = callback_data
        self.write_json()
        return hash_

    def get_data_by_hash(self, hash_):
        callback_data = self.data[hash_]
        return callback_data

    def clear_hash(self, hash_):
        if hash_ not in self.data:
            return
        del self.data[hash_]
        self.write_json()
