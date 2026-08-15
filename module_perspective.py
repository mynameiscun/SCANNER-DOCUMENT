import cv2 
import numpy as np
from module_rotate_resize import zoom_pic
# Sắp xếp điểm theo thứ tự
def order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect
#  Nắn ảnh
def transform_perspective(img, corners_4pts, output_size=(600, 800)):
    # Ép kiểu dữ liệu 4 điểm vừa chấm thành float32 để OpenCV tính toán
    rect = order_points(np.array(corners_4pts, dtype="float32"))
    (w, h) = output_size
    dst = np.array([
        [0, 0],
        [w - 1, 0],
        [w - 1, h - 1],
        [0, h - 1]
    ], dtype="float32")
    matrix = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(img, matrix, (w, h))

def mouse_click_event(event, x, y, flags, param):
    global selected_points, step1_img, img_display
    # Bắt sự kiện click chuột trái
    if event == cv2.EVENT_LBUTTONDOWN:
        if len(selected_points) < 4:
            # Lưu tọa độ
            selected_points.append([x, y])
            print(f"Điểm: ({x}, {y})")
            # chấm đỏ lên ảnh hiển thị
            cv2.circle(img_display, (x, y), 5, (0, 0, 255), -1)
            cv2.imshow("Chon 4 goc", img_display)
            # Đủ 4 điểm -> nắn ảnh
            if len(selected_points) == 4:
                print("Đã đủ 4 điểm! Đang nắn ảnh...")
                # Lấy ảnh sạch (step1_img) đem đi nắn với 4 điểm vừa chấm
                scanned_doc = transform_perspective(step1_img, selected_points, output_size=(600, 800))
                cv2.imshow("Anh Scan hoan chinh", scanned_doc)

if __name__ == "__main__":
    selected_points = [] # Danh sách chứa tọa độ 4 góc khi click
    step1_img = None     # Ảnh sạch (chưa vẽ chấm đỏ) dùng để nắn
    img_display = None   # Ảnh dùng để hiển thị và vẽ chấm đỏ lên
    # Đọc ảnh gốc
    raw_img = cv2.imread("Nhap/anh.jpg")
    if raw_img is not None:
        step1_img = zoom_pic(raw_img, scale=0.3)
        img_display = step1_img.copy()
        cv2.imshow("Chon 4 goc", img_display)
        # Gắn hàm lắng nghe sự kiện chuột vào cửa sổ này
        cv2.setMouseCallback("Chon 4 goc", mouse_click_event)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        print("Không đọc được ảnh! Vui lòng kiểm tra lại đường dẫn.")