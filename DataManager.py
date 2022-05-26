import json

class DataManager:
    def __init__(self) -> None:
        self.data = self.readJson()

    def readJson(self):
        with open("projectsData.json") as readFile:
            dataFromJson = json.load(readFile)
        return dataFromJson

    def writeJson(self):
        with open("projectsData.json", 'w') as writeFile:
            json.dump(self.data, writeFile)

    def updateJson(self, project, task="", name="", times={}):
        dataFromJson = self.readJson()
        if project not in dataFromJson:
            dataFromJson[project] = {}
        if task not in dataFromJson and task != "":
            dataFromJson[task] = {}
        if name not in dataFromJson and name != "":
            dataFromJson[name] = {}
        if times != {}:
            dataFromJson[project][task][name] = times
        self.data = dataFromJson
        self.writeJson()