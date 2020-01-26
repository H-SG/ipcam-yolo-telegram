import yaml

config = None

def loadConfig(configPath):
    global config
    with open(configPath, 'r') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

def saveConfig(configPath):
    global config
    with open(configPath, 'w') as f:
        yaml.dump(config, f)