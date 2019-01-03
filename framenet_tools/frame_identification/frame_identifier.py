import torch
import torch.nn as nn
from torchtext import data

from framenet_tools.frame_identification.reader import Data_reader
from framenet_tools.frame_identification.frame_id_network import Frame_id_network

use_cuda = True
batch_size = 1

# The files generated by pyfn
train_file = ["../data/experiments/xp_001/data/train.sentences", "../data/experiments/xp_001/data/train.frame.elements"]
dev_file = ["../data/experiments/xp_001/data/dev.sentences", "../data/experiments/xp_001/data/dev.frames"]
test_file = ["../data/experiments/xp_001/data/test.sentences", "../data/experiments/xp_001/data/test.frames"]
# Exemplary raw file
raw_file = ["../data/experiments/xp_001/data/WallStreetJournal20150915.txt"]


class Frame_Identifier(object):

	# Standard calculation for F1 score, taken from Open-SESAME
	def calc_f(self, tp, fp, fn):
		if tp == 0.0 and fp == 0.0:
			pr = 0.0
		else:
			pr = tp / (tp + fp)
		if tp == 0.0 and fn == 0.0:
			re = 0.0
		else:
			re = tp / (tp + fn)
		if pr == 0.0 and re == 0.0:
			f = 0.0
		else:
			f = 2.0 * pr * re / (pr + re)
		return pr, re, f

	def get_dataset(self, file, predict_FEEs):
		"""
		Loads the dataset and combines the necessary data

		:param file: A list of the two files to load
		:param predict_FEEs: A boolean whether to predict the frame evoking elements
		:return: xs: A list of senctences appended with its FEE
				ys: A list of frames corresponding to the given sentences
		"""
		reader = Data_reader()
		if len(file) == 2:
			reader.read_data(file[0], file[1])
		else:
			reader.read_raw_text(file[0])

		if predict_FEEs:
			reader.predict_fees()

		xs = []
		ys = []

		for annotation_sentences in reader.annotations:
			for annotation in annotation_sentences:
				xs.append([annotation.fee_raw] + annotation.sentence)
				ys.append(annotation.frame)

		return xs, ys

	def prepare_dataset(self, xs, ys):
		''' Prepares the dataset and returns a BucketIterator of the dataset

			Args:
				xs: A list of senctences
				ys: A list of frames corresponding to the given sentences

			Returns:
				A BucketIterator of the dataset

		'''
		examples = [data.Example.fromlist([x, y], self.data_fields) for x, y in zip(xs, ys)]

		dataset = data.Dataset(examples, fields=self.data_fields)

		# input_field.build_vocab(dataset)
		# output_field.build_vocab(dataset)

		# print(output_field.vocab.itos)

		iterator = data.BucketIterator(dataset, batch_size=batch_size, shuffle=False)

		return iterator

	'''
	def reformat_dataset(self, predictions, xs, ys):
		dataset = []
		i = 0

		for x in xs:


			while x[1] == ys[i][1]:
				dataset.append([])

				i += 1


		return dataset
	'''

	def evaluate(self, predictions, xs, file):

		# Load correct answers for comparison:
		gold_xs, gold_ys = self.get_dataset(file, False)

		tp = 0
		fp = 0
		fn = 0

		print(len(predictions))
		print(len(xs))
		# print(len(ys))

		# dataset = reformat_dataset(predictions, xs, ys)
		found = False

		for gold_x, gold_y in zip(gold_xs, gold_ys):
			for x, y in zip(xs, predictions):
				if gold_x == x and gold_y == self.output_field.vocab.itos[y.item()]:
					found = True
					break

			if found:
				tp += 1
			else:
				fn += 1

			found = False

		for x, y in zip(xs, predictions):
			for gold_x, gold_y in zip(gold_xs, gold_ys):
				if gold_x == x and gold_y == self.output_field.vocab.itos[y.item()]:
					found = True

			if not found:
				fp += 1

			found = False

		print(tp, fp, fn)

		return self.calc_f(tp, fp, fn)

	def write_predictions(self, predictions, xs):

		for prediction, x in zip(predictions, xs):
			print(x)
			print(self.output_field.vocab.itos[prediction.item()])

	def train(self):

		xs, ys = self.get_dataset(train_file, False)

		# print(xs[0])
		# print(ys[0])

		# Load with predicted FEEs
		# dev_xs, dev_ys = self.get_dataset(dev_file, True)

		dev_xs, dev_ys = self.get_dataset(raw_file, True)

		complete_xs = xs + dev_xs
		complete_ys = ys + dev_ys

		# Create fields
		self.input_field = data.Field(dtype=torch.float, use_vocab=True,
									  preprocessing=None)  # , fix_length= max_length) #No padding necessary anymore, since avg
		self.output_field = data.Field(dtype=torch.long)
		self.data_fields = [('Sentence', self.input_field), ('Frame', self.output_field)]

		# Zip datasets and generate complete dictionary
		examples = [data.Example.fromlist([x, y], self.data_fields) for x, y in zip(complete_xs, complete_ys)]

		dataset = data.Dataset(examples, fields=self.data_fields)

		self.input_field.build_vocab(dataset)
		self.output_field.build_vocab(dataset)

		print(self.output_field.vocab.itos)

		# print(dev_xs[0])
		# print(dev_ys[0])

		# additional_dev_xs, additional_dev_ys = self.get_dataset(dev_file, True)
		# dev_xs = [i[0] for i in additional_dev_xs]
		# print(len(additional_dev_xs))
		# exit()
		# No info on ys needed, but field is required as a complete dataset is needed
		# dev_ys = ['Default']*len(additional_dev_xs)

		dataset_size = len(xs)

		train_iter = self.prepare_dataset(xs, ys)
		dev_iter = self.prepare_dataset(dev_xs, dev_ys)

		self.input_field.vocab.load_vectors("glove.6B.300d")
		# dev_input_field.vocab.load_vectors("glove.6B.300d")

		input_count = len(self.input_field.vocab)
		num_classes = len(self.output_field.vocab)

		embed = nn.Embedding.from_pretrained(self.input_field.vocab.vectors)

		network = Frame_id_network(True, embed, num_classes)

		network.train_model(train_iter, dataset_size, batch_size)

		predictions = network.predict(dev_iter)
		# print(predictions)
		# print(self.evaluate(predictions, dev_xs, dev_file))

		self.write_predictions(predictions, dev_xs)

# acc = network.eval_model(dev_iter)

# print(acc)


f_i = Frame_Identifier()
f_i.train()
