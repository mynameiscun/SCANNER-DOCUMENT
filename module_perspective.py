import cv2
import numpy as np

WINDOW_NAME = "Chon diem tu do"

def fit_screen(img, max_width=800, max_height=700):
    h, w = img.shape[:2]
    scale = min(max_width / w, max_height / h)
    if scale < 1.0:
        return cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return img

def distance(p1, p2):
    return np.linalg.norm(np.array(p1) - np.array(p2))

def smart_sort_points(pts):
    pts = np.array(pts, dtype="float32")

    # Nếu chỉ chọn 4 điểm (Ảnh phẳng)
    if len(pts) == 4:
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)] # trái-trên
        rect[2] = pts[np.argmax(s)] # phải- dưới
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)] # phải -trên
        rect[3] = pts[np.argmax(diff)] # trái-dưới
        return rect, None, None
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)

    pt_TL = pts[np.argmin(s)]
    pt_BR = pts[np.argmax(s)]
    pt_TR = pts[np.argmin(diff)]
    pt_BL = pts[np.argmax(diff)]

    outer_rect = np.array([pt_TL, pt_TR, pt_BR, pt_BL], dtype="float32")

    # Lọc ra các điểm nằm ở giữa (không phải 4 góc biên) để làm điểm nếp gấp
    inner_pts = []
    for p in pts:
        # Nếu điểm không trùng với 4 góc chính thì là điểm giữa
        if not any(np.array_equal(p, corner) for corner in outer_rect):
            inner_pts.append(p)

    inner_pts = np.array(inner_pts, dtype="float32")

    if len(inner_pts) >= 2:
        # Tách các điểm giữa thành bên Trái (ML) và bên Phải (MR) dựa vào tọa độ X trung bình
        center_x = np.mean(inner_pts[:, 0])
        left_mids = inner_pts[inner_pts[:, 0] < center_x]
        right_mids = inner_pts[inner_pts[:, 0] >= center_x]

        pt_ML = np.mean(left_mids, axis=0) if len(left_mids) > 0 else inner_pts[0]
        pt_MR = np.mean(right_mids, axis=0) if len(right_mids) > 0 else inner_pts[-1]
    elif len(inner_pts) == 1:
        pt_ML = inner_pts[0]
        pt_MR = inner_pts[0]
    else:
        pt_ML = (pt_TL + pt_BL) / 2
        pt_MR = (pt_TR + pt_BR) / 2

    return outer_rect, pt_ML, pt_MR
    #  hàm chính
def process_scanned_image(img, pts):
    n_pts = len(pts)
    if n_pts < 4:
        return None

    if n_pts == 4:
        rect, _, _ = smart_sort_points(pts)
        (tl, tr, br, bl) = rect
        maxWidth = max(int(distance(br, bl)), int(distance(tr, tl)))
        maxHeight = max(int(distance(tr, br)), int(distance(tl, bl)))
        dst = np.array([[0, 0], [maxWidth - 1, 0], [maxWidth - 1, maxHeight - 1], [0, maxHeight - 1]], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(img, M, (maxWidth, maxHeight))
    else:
        outer_rect, pt_ML, pt_MR = smart_sort_points(pts)
        pt_TL, pt_TR, pt_BR, pt_BL = outer_rect[0], outer_rect[1], outer_rect[2], outer_rect[3]

        # Tách riêng chiều rộng cho nửa trên và nửa dưới để giữ đúng tỷ lệ thực tế
        W_top = int((distance(pt_TL, pt_TR) + distance(pt_ML, pt_MR)) / 2)
        W_bot = int((distance(pt_ML, pt_MR) + distance(pt_BL, pt_BR)) / 2)

        # Tính chiều cao thực tế của từng nửa dựa trên tỷ lệ hình học nguyên bản
        H1 = int((distance(pt_TL, pt_ML) + distance(pt_TR, pt_MR)) / 2)
        H2 = int((distance(pt_ML, pt_BL) + distance(pt_MR, pt_BR)) / 2)

        # Xử lý nửa trên với chiều rộng và chiều cao riêng của nó
        src_top = np.array([pt_TL, pt_TR, pt_MR, pt_ML], dtype="float32")
        dst_top = np.array([[0, 0], [W_top, 0], [W_top, H1], [0, H1]], dtype="float32")
        M_top = cv2.getPerspectiveTransform(src_top, dst_top)
        img_top = cv2.warpPerspective(img, M_top, (W_top, H1))

        # Xử lý nửa dưới
        src_bot = np.array([pt_ML, pt_MR, pt_BR, pt_BL], dtype="float32")
        dst_bot = np.array([[0, 0], [W_top, 0], [W_top, H2], [0, H2]], dtype="float32") # Ép chung W_top để khớp bề ngang
        M_bot = cv2.getPerspectiveTransform(src_bot, dst_bot)
        img_bot = cv2.warpPerspective(img, M_bot, (W_top, H2))

        return cv2.vconcat([img_top, img_bot])

def mouse_click_event(event, x, y, flags, param):
    global selected_points, img_display

    if event == cv2.EVENT_LBUTTONDOWN:
        selected_points.append([x, y])
        idx = len(selected_points)
        print(f"Điểm {idx}: ({x}, {y})")

        cv2.circle(img_display, (x, y), 5, (0, 0, 255), -1)
        cv2.putText(img_display, str(idx), (x + 10, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.imshow(WINDOW_NAME, img_display)

if __name__ == "__main__":
    selected_points = []
    raw_img = cv2.imread("Nhap/anhthu2.jpg")

    if raw_img is not None:
        scale_factor = 0.3
        h, w = raw_img.shape[:2]
        img_display = cv2.resize(raw_img, (int(w * scale_factor), int(h * scale_factor)))

        print("- Click tự do 4 góc ngoài cùng và các điểm nếp gấp ở giữa.")
        print("- Bấm phím [ENTER] để thuật toán tự động phân tách và xử lý!")

        cv2.imshow(WINDOW_NAME, img_display)
        cv2.setMouseCallback(WINDOW_NAME, mouse_click_event)

        while True:
            key = cv2.waitKey(1) & 0xFF
            if key == 13: # Phím Enter
                if len(selected_points) < 4:
                    print("Vui lòng chọn ít nhất 4 điểm!")
                    continue

                original_pts = [[int(pt[0] / scale_factor), int(pt[1] / scale_factor)] for pt in selected_points]

                final_img = process_scanned_image(raw_img, original_pts)

                if final_img is not None:
                    cv2.imshow(" Anh da Scan", fit_screen(final_img))
                break
            elif key == ord('q'):
                print("Đã hủy.")
                break
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        print("Không đọc được ảnh!")