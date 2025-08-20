from json import dump, load
from typing import Dict


class Settings:
    def __init__(self, file_name: str = 'Settings.json') -> None:
        self.__file_settings(file_name)

    def __file_settings(self, file_name: str) -> Dict:
        with open(file_name, 'r') as file:
            self.settings_dict: dict = load(file)
        return self.settings_dict

    def key(self, key: str) -> str:
        for i, value in self.settings_dict.items():
            if i == key:
                return value
        return ''

    def update_json(self, key: str, value: str | None) -> None:
        with open('Settings.json', 'r') as file:
            data = load(file)

        data[key] = value

        # Salvando as alterações de volta no arquivo
        with open('Settings.json', 'w') as file:
            dump(data, file, indent=2)

if __name__ == '__main__':
    s = Settings('Settings.json')