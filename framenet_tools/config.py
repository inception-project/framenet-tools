import os
import configparser
import re

CONFIG_PATH = "config.file"


class ConfigManager(object):
    def __init__(self):

        self.train_files = []
        self.eval_files = []

        # NOTE: model is actually saved in three individual files (.ph, .in_voc, .out_voc)
        model_name = "model"
        dir_models = "data/models/"
        self.saved_model = os.path.join(dir_models, model_name)

        self.use_cuda = True

        self.all_files = self.train_files + self.eval_files

        self.hidden_sizes = [512, 256]
        self.activation_functions = ["ReLU", "ReLU"]
        self.batch_size = 10
        self.num_epochs = 5
        self.learning_rate = 0.001
        self.embedding_size = 300

        if not self.load_config():
            self.create_config()

    def load_defaults(self):
        """
        Loads the builtin defaults

        :return:
        """

        # NOTE this path is also the default path for pyfn
        dir_data = "data/experiments/xp_001/data/"

        # The files generated by pyfn
        train_files = ["train.sentences", "train.frame.elements"]
        dev_files = ["dev.sentences", "dev.frames"]
        test_files = ["test.sentences", "test.frames"]

        self.train_files = [train_files]
        self.eval_files = [dev_files, test_files]

        for handle in self.train_files:
            handle[0] = os.path.join(dir_data, handle[0])
            handle[1] = os.path.join(dir_data, handle[1])

        for handle in self.eval_files:
            handle[0] = os.path.join(dir_data, handle[0])
            handle[1] = os.path.join(dir_data, handle[1])

    def load_config(self):
        """
        Loads the config file and saves all found variables

        NOTE: If no config file was found, the default configs will be loaded instead

        :return: A boolean - True if the config file was loaded, False if defaults were loaded
        """

        if not os.path.isfile(CONFIG_PATH):
            self.load_defaults()
            return False

        config = configparser.ConfigParser()
        config.read(CONFIG_PATH)

        for section in config.sections():

            if section == "TRAINPATHS":
                for key in config[section]:

                    path = config[section][key].rsplit("\t")
                    self.train_files.append(path)

            if section == "EVALPATHS":
                for key in config[section]:

                    path = config[section][key].rsplit("\t")
                    self.eval_files.append(path)

            if section == "VARIABLES":
                for key in config[section]:
                    if key == "model_path":
                        self.saved_model = config[section][key]

                    if key == "use_cuda":
                        self.use_cuda = config[section][key] == "True"

            if section == "HYPERPARAMETER":
                for key in config[section]:
                    if key == "hidden_sizes":
                        # Find numbers and convert to int using regex
                        found_numbers = re.findall(r"[0-9]+", config[section][key])
                        self.hidden_sizes = [int(t) for t in found_numbers]

                    if key == "activation_functions":
                        self.activation_functions = re.findall(
                            r"\w+", config[section][key]
                        )

                    if key == "batch_size":
                        self.batch_size = int(config[section][key])

                    if key == "num_epochs":
                        self.num_epochs = int(config[section][key])

                    if key == "learning_rate":
                        self.learning_rate = float(config[section][key])

                    if key == "embedding_size":
                        self.embedding_size = int(config[section][key])

        return True

    def paths_to_string(self, files: list):
        """
        Helper function for turning a list of file paths into a structured string

        :param files: A list of files
        :return: The string containing all files
        """

        string = ""

        for handle in files:
            string += (
                handle[0].rsplit(".")[0].rsplit("/")[-1]
                + ": "
                + handle[0]
                + "\t"
                + handle[1]
                + "\n"
            )

        string += "\n"

        return string

    def create_config(self):
        """
        Creates a config file and saves all necessary variables

        :return:
        """

        config_string = "[TRAINPATHS]\n"
        config_string += self.paths_to_string(self.train_files)

        config_string += "[EVALPATHS]\n"
        config_string += self.paths_to_string(self.eval_files)

        config_string += "[VARIABLES]\n"
        config_string += "model_path: " + self.saved_model + "\n"
        config_string += "use_cuda: " + str(self.use_cuda) + "\n"

        config_string += "\n[HYPERPARAMETER]\n"
        config_string += "hidden_sizes: " + str(self.hidden_sizes) + "\n"
        config_string += (
            "activation_functions: " + str(self.activation_functions) + "\n"
        )
        config_string += "batch_size: " + str(self.batch_size) + "\n"
        config_string += "num_epochs: " + str(self.num_epochs) + "\n"
        config_string += "learning_rate: " + str(self.learning_rate) + "\n"
        config_string += "embedding_size: " + str(self.embedding_size) + "\n"

        file = open(CONFIG_PATH, "w")
        file.write(config_string)
        file.close()
