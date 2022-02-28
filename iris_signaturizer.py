import cv2
import numpy as np
from operator import itemgetter
import pywt


class IrisSignaturizer:
    """docstring for IrisRecognizer"""

    def __init__(self, subjects, images):
        self.subjects = subjects
        self.images = images
        self.normalized_irises = []
        self.signatures = []

    # @@@@@@@@@@@@@@@@@@@@@@@@@ PUBLIC INTERFACE @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    def generate_signatures(self):
        # TODO: Transform this into multiprocess
        for image in self.images:
            self.signaturize_image(image)
    # @@@@@@@@@@@@@@@@@@@@@@@ END PUBLIC INTERFACE @@@@@@@@@@@@@@@@@@@@@@@@@@@@
    def signaturize_image(self, image):
        processed_img = self.pre_process_img(image)
        x_pupil, y_pupil, r_pupil = self.find_pupil(processed_img)
        pupil_coords = (x_pupil, y_pupil, r_pupil)
        x_iris, y_iris, r_iris = self.find_iris(pupil_coords, image)
        iris_coords = (x_iris, y_iris, r_iris)
        normalized_iris = self.normalize_iris(
            pupil_coords, iris_coords, image)
        self.normalized_irises.append(normalized_iris)
        signature = self.get_image_signature(normalized_iris)
        self.signatures.append(signature)

    def find_pupil(self, image):
        accumulator_threshold = 150
        circles = None
        while circles is None:
            circles = cv2.HoughCircles(image, cv2.HOUGH_GRADIENT,
                                       1, 1, param2=accumulator_threshold)
            accumulator_threshold = accumulator_threshold - 1
        circles = np.uint16(np.around(circles[0, :]))
        return circles[0]

    def get_points_near_circle_perimeter(self, x, y, r, img, n_of_points=360):
        points = []
        distance_of_points = (2 * np.pi) / n_of_points
        for i in range(n_of_points):
            teta = i * distance_of_points
            y_p = y + int(r * np.cos(teta))
            x_p = x + int(r * np.sin(teta))
            points.append(img[y_p][x_p])
        return np.array(points)

    def find_iris(self, pupil_coords, img, value=4):
        x_pupil, y_pupil, r_pupil = pupil_coords
        image = cv2.equalizeHist(img)
        n_of_rows, n_of_columns = img.shape
        max_r = min((n_of_rows - y_pupil, n_of_columns - x_pupil))
        x, y, r_b = x_pupil, y_pupil, r_pupil
        r_a = r_b + 5
        variations = []
        points_before = self.get_points_near_circle_perimeter(x, y, r_b, image)
        iterations = 0
        max_iterations = 30
        while r_a < max_r and iterations < max_iterations:
            points_after = self.get_points_near_circle_perimeter(
                x, y, r_a, image)
            variations.append((r_a, sum(abs(points_after - points_before))))
            points_before = points_after
            r_a += 5
            iterations += 1
        return x, y, max(variations, key=itemgetter(1))[0]

    def pre_process_img(self, image):
        img = image
        img_with_blur = cv2.medianBlur(img, 25)
        _, im_th = cv2.threshold(img_with_blur, 25, 255, cv2.THRESH_BINARY)
        canny = cv2.Canny(im_th, 50, 200)
        cv2.imshow("Original Image", image)
        cv2.imshow("Thresholded Image", im_th)
        # cv2.waitKey(0)
        return canny

    def normalize_iris(self, pupil_coords,
                       iris_coords,
                       image, n_of_divisions=360):
        x_pupil, y_pupil, r_pupil = pupil_coords
        x_iris, y_iris, r_iris = iris_coords
        distance_of_each_division = (2 * np.pi) / n_of_divisions
        normalized_image = []
        for division in range(n_of_divisions):
            teta = distance_of_each_division * division
            points = []
            for radius in range(int(r_pupil), int(r_iris + 1)):
                y_p = y_iris + int(radius * np.cos(teta))
                x_p = x_iris + int(radius * np.sin(teta))
                points.append(image[y_p][x_p])
            normalized_image.append(points)
        normalized_image = np.array(normalized_image).T
        resized_image = cv2.resize(normalized_image,
                                   (256, 32), interpolation=cv2.INTER_CUBIC)
        return resized_image

    def binarize_signature(self, matrix):
        signature = []
        for array in matrix:
            for element in array:
                if element >= 0:
                    signature.append(1)
                else:
                    signature.append(0)
        return signature

    def get_image_signature(self, image):
        cA, _ = pywt.dwt2(image, 'haar')
        cA, _ = pywt.dwt2(cA, 'haar')
        cA, _ = pywt.dwt2(cA, 'haar')
        cA, (cH, cV, cD) = pywt.dwt2(cA, 'haar')
        return self.binarize_signature(cH + cV + cD)
