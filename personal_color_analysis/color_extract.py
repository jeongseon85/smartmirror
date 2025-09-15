# personal_color_analysis/color_extract.py

import cv2
import numpy as np
from sklearn.cluster import KMeans
from itertools import compress

class DominantColors:
    CLUSTERS = None
    IMAGE = None
    COLORS = None
    LABELS = None

    def __init__(self, image, clusters=3):
        self.CLUSTERS = clusters
        img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        self.IMAGE = img.reshape((img.shape[0] * img.shape[1], 3))

        kmeans = KMeans(n_clusters=self.CLUSTERS, n_init=10) # n_init=10 추가
        kmeans.fit(self.IMAGE)

        self.COLORS = kmeans.cluster_centers_
        self.LABELS = kmeans.labels_

    def getHistogram(self):
        numLabels = np.arange(0, self.CLUSTERS + 1)
        (hist, _) = np.histogram(self.LABELS, bins=numLabels)
        hist = hist.astype("float")
        hist /= hist.sum()

        colors = self.COLORS
        colors = colors[(-hist).argsort()]
        hist = hist[(-hist).argsort()]
        for i in range(len(colors)):
            colors[i] = colors[i].astype(int)

        # 파란색 마스크 제거 (피부, 눈썹, 눈 색상에서 파란색을 제외)
        fil = [colors[i][2] < 250 and colors[i][0] > 10 for i in range(len(colors))]
        colors = list(compress(colors, fil))
        return colors, hist