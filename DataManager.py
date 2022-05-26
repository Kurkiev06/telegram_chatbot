import json

class DataManager:
    def __init__(self) -> None:
        self.data = self.readJson()

    def readJson(self) -> dict:
        with open("projectsData.json") as readFile:
            dataFromJson = json.load(readFile)
        return dataFromJson

    def writeJson(self):
        with open("projectsData.json", 'w') as writeFile:
            json.dump(self.data, writeFile)

    def updateJson(self, project, task="", name="", times={}):
        self.data = self.readJson()
        name = name.lower()
        if project not in self.data:
            self.data[project] = {}
        if task != "" and task not in self.data[project]:
            self.data[project][task] = {}
        if name != "" and name not in self.data[project][task]:
            self.data[project][task][name] = {}
        if times != {}:
            self.data[project][task][name] = times
        self.writeJson()