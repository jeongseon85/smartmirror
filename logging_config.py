
import logging, os

def setup_logging(log_dir='logs', filename='app.log', level=logging.INFO):
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, filename)

    logger = logging.getLogger()
    logger.setLevel(level)

    # Avoid duplicate handlers if called twice
    if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
        fh = logging.FileHandler(log_path, encoding='utf-8')
        fh.setLevel(level)
        fmt = logging.Formatter('[%(asctime)s] %(levelname)s %(name)s: %(message)s')
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        ch = logging.StreamHandler()
        ch.setLevel(level)
        fmt = logging.Formatter('%(levelname)s: %(message)s')
        ch.setFormatter(fmt)
        logger.addHandler(ch)

    logging.info('Logging initialized → %s', log_path)
    return log_path
