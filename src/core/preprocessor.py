# src/core/preprocessor.py
import cv2

class ImagePreprocessor:
    """
    [비전 처리 담당자]
    OCR 인식률을 극대화하기 위해 이미지를 보정합니다.
    """
    def enhance_image(self, image):
        """
        단일 이미지를 입력받아 노이즈 제거 및 보정을 수행합니다.

        Args:
            image (numpy.ndarray): OpenCV로 읽어온 BGR 이미지 데이터ㅡ

        Returns:
            numpy.ndarray: 전처리가 완료된 이미지
        """
        # TODO: OpenCV(cv2)를 활용하여 흑백(Grayscale) 변환
        # TODO: 이진화(Binarization) 처리 (배경은 하얗게, 글자는 까맣게)
        # TODO: 스캔 과정에서 삐뚤어진 이미지 기울기 보정 (Deskewing)

        # TODO 1: 그레이스케일(Grayscale)  변환 수행 (cv2.cvtColor 활용)
        if len(image.shape) == 3:  # 컬러 이미지인 경우
            processed_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            processed_image = image.copy()

        return processed_image
        # TODO 2: 가우시안 블러(Gaussian Blur)를 적용하여 미세한 스캔 노이즈 제거

        # TODO 3: 어댑티브 임계값 처리(Adaptive Thresholding)로 이진화 수행
        # 참고: 배경은 하얗게(255), 글자는 까맣게(0) 처리되는지 확인 (cv2.THRESH_BINARY)

        # TODO 4: 이미지 기울기 보정(Deskewing) 로직 호출
        # 텍스트의 최소 면적 사각형(minAreaRect)을 찾아 수평 각도만큼 회전 변환 적용

        # TODO 5: (선택) 모폴로지 팽창/침식 연산을 통해 끊어진 표의 선을 보정
        # return processed_image
        pass

    def _get_skew_angle(self, binary_image):
        """
        이미지의 기울기 각도를 계산하는 내부 메서드
        """
        # TODO: 이미지 내의 텍스트 픽셀 좌표를 추출하여 회전 각도 산출
        pass

    def _rotate_image(self, image, angle):
        """
        계산된 각도만큼 이미지를 회전시키는 내부 메서드
        """
        # TODO: 이미지 중심점을 기준으로 회전 행렬 생성 및 아핀 변환(warpAffine) 적용
        pass
