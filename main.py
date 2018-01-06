import os
import argparse
import torch
import torch.optim as optim
import torch.nn.functional as F
from torch.autograd import Variable
import python_format as dataset
import transformer


def gen(batch_size):
  g = dataset.gen(min_len=3, max_len=5)

  while True:
    xs, ys = [], []

    for i in range(batch_size):
      x, y = next(g)
      xs.append(x)
      ys.append(y)

    x_len = [len(x) for x in xs]
    y_len = [len(y) for y in ys]

    x = [x + [dataset.eos] + [dataset.pad] * (max(x_len) - len(x)) for x in xs]
    y = [y + [dataset.eos] + [dataset.pad] * (max(y_len) - len(y)) for y in ys]

    x = torch.LongTensor(x)
    y = torch.LongTensor(y)
    yield (x, y)


def main():
  # TODO: visualize attention
  parser = argparse.ArgumentParser()
  parser.add_argument("--weights", help="weight file", type=str, required=True)
  parser.add_argument("--batch-size", help="batch size", type=int, default=32)
  parser.add_argument("--size", help="transformer size", type=int, default=128)
  parser.add_argument("--cuda", help="use cuda", action='store_true')
  parser.add_argument(
      "--learning-rate", help="learning rate", type=float, default=0.001)
  parser.add_argument(
      "--dropout", help="dropout probability", type=float, default=0.2)
  args = parser.parse_args()

  steps = 1000
  log_interval = 10

  model = transformer.Tranformer(
      source_vocab_size=dataset.vocab_size,
      target_vocab_size=dataset.vocab_size,
      size=args.size,
      n_layers=2,
      n_heads=4,
      dropout=args.dropout,
      padding_idx=dataset.pad)
  if args.cuda:
    model = model.cuda()

  if os.path.exists(args.weights):
    model.load_state_dict(torch.load(args.weights))

  optimizer = optim.Adam(model.parameters(), lr=args.learning_rate)

  model.train()
  for i, (x, y) in zip(range(steps), gen(args.batch_size)):
    optimizer.zero_grad()

    x, y = Variable(x), Variable(y)
    if args.cuda:
      x, y = x.cuda(), y.cuda()

    y_bottom, y = y[:, :-1], y[:, 1:]

    y_top = model(x, y_bottom)
    loss = transformer.loss(y_top=y_top, y=y)
    accuracy = transformer.accuracy(y_top=y_top, y=y)
    accuracy = accuracy * 100

    if i % log_interval == 0:
      print(
          'step: {}, loss: {:.4f}, accuracy: {:.2f}\n\ttrue: {}\n\tpred: {}\n'.
          format(
              i,
              loss.data[0],
              accuracy.data[0],
              dataset.decode(y.data[0]),
              dataset.decode(torch.max(y_top, dim=-1)[1].data[0]),
          ))

      torch.save(model.state_dict(), args.weights)

    loss.backward()
    optimizer.step()


if __name__ == '__main__':
  main()
