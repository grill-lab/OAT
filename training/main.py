import argparse

from utils import logger
import train_intent_classifier

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-b", "--batch_size", help="Training batch size", default=32, type=int)
    parser.add_argument("-s", "--seed", help="Random seed", default=42, type=int)
    parser.add_argument("-a", "--batch_accum", help="batch_accum", default=1, type=int)
    parser.add_argument("-g", "--grad_steps", help="grad_steps", default=2000, type=int)
    parser.add_argument("-d", "--dev_steps", help="dev_steps", default=400, type=int)
    parser.add_argument("-e", "--only_eval", help="only run evaluation, no training", action='store_true')
    args = parser.parse_args()
    logger.info("Training container has started with configuration:")
    logger.info(f"batch_size = {args.batch_size}")
    logger.info(f"seed = {args.seed}")
    logger.info(f"batch_accum = {args.batch_accum}")
    logger.info(f"grad_steps = {args.grad_steps}")
    logger.info(f"dev_steps = {args.dev_steps}")
    logger.info(f"only_eval = {args.only_eval}")
    train_intent_classifier.train(args)
