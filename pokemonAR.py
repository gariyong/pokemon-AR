import numpy as np
import cv2 as cv


def draw_pokemon(img, img_pokemon, img_pts):
    # 포켓몬 이미지의 네 모서리 좌표
    h, w = img_pokemon.shape[:2]
    src_pts = np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype=np.float32)

    # 3D에서 투영된 2D 좌표 (img_pts)로 호모그래피 계산
    dst_pts = img_pts.astype(np.float32)
    M = cv.getPerspectiveTransform(src_pts, dst_pts)

    # 이미지 왜곡 변환 (체스보드 위에 세우기)
    warped = cv.warpPerspective(
        img_pokemon,
        M,
        (img.shape[1], img.shape[0]),
        flags=cv.INTER_LINEAR,
        borderMode=cv.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0),
    )

    # 투명도(Alpha 채널)를 이용한 합성
    alpha_map = warped[:, :, 3] / 255.0
    for c in range(0, 3):
        img[:, :, c] = alpha_map * warped[:, :, c] + (1 - alpha_map) * img[:, :, c]


if __name__ == "__main__":
    # 1. 캘리브레이션 데이터 로드
    K = np.array(
        [
            [1.77140702e03, 0.00000000e00, 9.55399078e02],
            [0.00000000e00, 1.77337532e03, 5.30616680e02],
            [0.00000000e00, 0.00000000e00, 1.00000000e00],
        ],
        dtype=np.float32,
    )
    dist_coeff = np.array(
        [
            2.70441194e-01,
            -1.40049730e00,
            -4.22498627e-03,
            -1.11865088e-05,
            2.32906714e00,
        ],
        dtype=np.float32,
    )

    # 2. 포켓몬 이미지 로드
    pokemon = cv.imread("pokemon.webp", cv.IMREAD_UNCHANGED)
    if pokemon is None:
        print("포켓몬 이미지를 찾을 수 없습니다!")
        exit()

    video = cv.VideoCapture("./recorded_video.mp4")
    board_pattern = (10, 7)
    board_cellsize = 0.025

    # 3D 공간에 세워질 포켓몬의 사각형 좌표 (수직으로 세움)
    # [x, y, z] -> 체스보드 바닥은 z=0, 위쪽은 z가 음수(카메라 방향)
    size = 0.1  # 포켓몬 크기
    offset_x = 0.05  # 오른쪽으로 이동
    offset_y = 0.1  # 아래로 이동

    obj_pokemon = np.array(
        [
            [offset_x, offset_y, -size],  # 좌상단
            [size + offset_x, offset_y, -size],  # 우상단
            [size + offset_x, offset_y, 0],  # 우하단
            [offset_x, offset_y, 0],  # 좌하단
        ],
        dtype=np.float32,
    )

    while True:
        valid, frame = video.read()
        if not valid:
            break

        gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        complete, pts = cv.findChessboardCorners(gray, board_pattern)

        if complete:
            # 카메라 자세 계산 (Pose Estimation)
            obj_pts = (
                np.array(
                    [
                        [c, r, 0]
                        for r in range(board_pattern[1])
                        for c in range(board_pattern[0])
                    ],
                    dtype=np.float32,
                )
                * board_cellsize
            )
            ret, rvec, tvec = cv.solvePnP(obj_pts, pts, K, dist_coeff)

            if ret:
                # 3D 포켓몬 좌표를 2D 화면 좌표로 투영
                img_pts, _ = cv.projectPoints(obj_pokemon, rvec, tvec, K, dist_coeff)
                img_pts = img_pts.reshape(-1, 2)

                # 포켓몬 그리기
                try:
                    draw_pokemon(frame, pokemon, img_pts)
                except:
                    pass

        cv.imshow("Pokemon AR", frame)
        if cv.waitKey(1) == 27:
            break

    video.release()
    cv.destroyAllWindows()
