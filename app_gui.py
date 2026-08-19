import customtkinter as ctk
import cv2
import tkinter as tk
# from tkinter import filedialog #làm cửa sổ chọn file
from tkinter import filedialog, Canvas #làm cửa sổ chọn file + canvas overlay
from PIL import Image, ImageTk#Canvas
from module_perspective import(process_scanned_image, smart_sort_points)
import numpy as np
from module_rotate_resize import(
    rotation_pic
    ,zoom_pic
)
#LẤY MÀU GIAO DIỆN
COLOR_BG = "#080812"          # đen tím
COLOR_NAVY = "#111A2E"        # navy
COLOR_NAVY_LIGHT = "#17213A"

COLOR_PURPLE = "#7C3AED"      # tím
COLOR_PURPLE_HOVER = "#6D28D9"

COLOR_BLUE = "#2563EB"

COLOR_TEXT = "#F4F4F8"
COLOR_TEXT_MUTED = "#9CA3AF"

COLOR_BORDER = "#26324A"

#cửa số chứa tất cả element
app = ctk.CTk()
app.title("Scanner Document GUI")
app.geometry("1500x900")
app.configure(fg_color=COLOR_BG) #set thuộc tính

ctk.set_appearance_mode("dark")  # Modes: "System" (standard), "Dark", "Light"
#----TẠO CÁC BIẾN ĐỂ LƯU TRẠNG THÁI CỦA ẢNH----
#Biến cho file
original_img = None #biến cho ảnh gốc (nguồn để mảnh 1,2 xử lý)

# ảnh dùng riêng cho Canvas
canvas_photo = None
# thông tin ảnh đang hiển thị
display_scale = 1.0
display_offset_x = 0
display_offset_y = 0
display_width = 0
display_height = 0

#Biến cho camera
camera = None # biến cho camera (dùng để mở camera)
camera_frame = None # biến cho frame camera (hiển thị trên giao diện)
camera_ctk_image = None # biến cho ảnh camera dạng ctk image (hiển thị trên giao diện)
camera_after_id = None#ID của after để cập nhật frame của cam liên tục (frame1,2,3,...)
#BIẾN CHO CHỨC NĂNG
#Zoom
fit_scale = 1.0# Scale để fit ảnh vào Canvas
zoom_scale = 1.0# Zoom do người dùng điều khiển
#Pan ảnh
pan_x = 0# ảnh thay đổi so với trung tâm
pan_y = 0
is_panning = 0
pan_last_x = 0#chuột vừa di chuyển bao nhiêu
pan_last_y = 0
#BIẾN LƯU 4 CORNERS
current_corners = []
corner_select_mode = False
dragging_corner = None #góc đang chọn để kéo (cho canvas kéo vùng chọn)
result_img = None
result_photo = None
scan_img = None #ảnh được mảnh 2 xử lý xong
# CẤU HÌNH CHÍNH CHO WIDGEETS CON CỦA APP (hàng và cột)
app.grid_rowconfigure(0, weight=1)
app.grid_columnconfigure(0, weight=0, minsize=240) #cột 0 là slide bar, nên đặt minsize=240
app.grid_columnconfigure(1, weight=1)
#app.grid_columnconfigure(2, weight=1)
#BIẾN CHO ẢNH ĐẦU RA 
result_fit_scale = 1.0
result_zoom_scale = 1.0
result_display_scale = 1.0
result_display_width = 0
result_display_height = 0
result_offset_x = 0
result_offset_y = 0
result_pan_x = 0
result_pan_y = 0
result_is_panning = False
result_last_x = 0
result_last_y = 0
#biến thao tác với mảnh 1
input_img = None # tránh dữ liệu bị cộng dồn khi thay đổi liên tục
rotate_angle = 0
resize_scale = 1.0
resize_method_var = tk.StringVar(
    value = "AUTO"
)
#----SLIDE BAR----
#tạo phần slidebar (bên trái)
sidebar = ctk.CTkFrame( app ,#slide bar là con của app
                        width= 240
                        , corner_radius=0
                        , fg_color=COLOR_NAVY)

#thiết lập grid cho slidebar
sidebar.grid(row=0
             , column=0 # đặt vào cột 0
             #columnspan=1 # mở rộng qua 1 cột
             , sticky="nsew")#nsew là kéo dài hết chiều cao và chiều rộng của ô grid
sidebar.grid_propagate(False)#không tự co theo các widgets con bên trong
#-------------------------------------------
#----HÀM HIỂN THỊ ẢNH CHUNG CHO TẤT CẢ----
#-------------------------------------------
def display_source_image():
    global canvas_photo, display_height, display_offset_x,display_offset_y,display_scale, display_width,zoom_scale, fit_scale,pan_x,pan_y
    if original_img is None:
        return
    
    #LẤY KÍCH THƯỚC CỦA CANVAS
    image_canvas.update_idletasks()
    canvas_width = image_canvas.winfo_width()
    canvas_height =  image_canvas.winfo_height()
    # CANVAS chưa render thì trả 
    if canvas_width <= 1 or canvas_height <= 1:
        return
    #LÁY KÍCH THƯỚC ẢNH THẬT ĐỂ TÍNH TOÁN
    img_height,img_width = original_img.shape[:2]#không lấy tensor chỉ lấy 2 giá trị w,h
    #TÍNH KÍCH THƯỚC SCALE ĐỂ HIỆN THỊ VỪA TRÊN KHUNG CANVAS
    scale_width = canvas_width / img_width # tính con số chênh lệch giữa ảnh gốc và canvas 
    scale_height = canvas_height / img_height
    
    #display_scale = min (scale_width,scale_height )# lấy theo số chênh leehcj nhỏ hơn tránh bị tràn
    #tách thành 2 hàm để thêm chức năng viewzoom
    fit_scale = min (scale_width,scale_height )
    display_scale= (fit_scale * zoom_scale)#tỷ lệ hiển thị cuối cùng = tỷ lệ vừa khung * tỷ lệ zoom của người dùng
    display_width = max(1, int(img_width * display_scale))#TÍNH LẠI kích thước sau ví dụ w gốc là 1920 -> sau scale còn 450
    display_height = max(1, int(img_height * display_scale))
    
    #TÍNH OFFSET ĐẺ ẢNH HIỂN THỊ VÀO GIỮA
    display_offset_x = (canvas_width - display_width) /2+ pan_x#đặt ảnh vào giữa và lấy thêm vị trí lệch so với trung tam (pan)
    display_offset_y = (canvas_height - display_height) /2 + pan_y
    
    #CHUYỂN ẢNH BGR SANG RGB
    img_rgb = cv2.cvtColor(
        original_img,
        cv2.COLOR_BGR2RGB
    )
    #CHUYỂN NUMPY SANG PIL (từ matrix sang dạng ctk có thể đọc)
    pil_img = Image.fromarray(img_rgb)
    
    #RESIZE ẢNH ĐỂ HIỂN THỊ
    pil_img = pil_img.resize(

        (
            display_width,
            display_height
        ),

        Image.Resampling.LANCZOS # hàm resize trong pillow tránh bị vỡ khi réize
        
    )
    #CHUYỂN PIL SANG TKINTER
    canvas_photo = ImageTk.PhotoImage(#thư viện imageTK đưa ảnh vào giao diện tkinter
        pil_img
    )
    #XÓA LABEL CŨ 
    image_canvas.delete("all")
    #CHÈN ẢNH MỚI LÊN CANVAS
    image_canvas.create_image(
        display_offset_x
        , display_offset_y
        , anchor = "nw"
        , image = canvas_photo
    )
    if len(current_corners) > 0:
        draw_scan_overlay()
#-------------------------------------------
#----HÀM LẤY NGUỒN ẢNH----
#-------------------------------------------
#Lấy từ file
def choose_file(dialog):
    global input_img,original_img#LẤY BIẾN TOÀN CỤC ĐỂ LƯU TRẠNG THÁI ẢNH
    #MỞ TỪ FILE
    file_path = filedialog.askopenfilename(#mở của sổ chọn file (chỉ là filepath không phải mở file)
        title = "Chọn ảnh tài liệu",
        filetypes = [("Image files", "*.jpg *.jpeg *.png *.bmp")
                     , ("All files", "*.*")]
    )
    if not file_path:
        return
    #ĐỌC BẰNG OPEN CV
    input_img = cv2.imread(file_path)#dùng để mở ảnh gốc, cv2 đọc ảnh ra dạng mảng numpy
    
    if input_img is None:
        print("Không thể mở ảnh:", file_path)
        return
    original_img = input_img.copy()
    clear_old_document_state()
    reset_view()
    #CHUYỂN TỪ BGR SANG RGB (OpenCV đọc ảnh theo định dạng BGR) cần chuyển sang RGB để hiển thị đúng màu
#    img_RGB = cv2.cvtColor(original_img
#                           , cv2.COLOR_BGR2RGB)
#    #NUMPY ARRAY SANG CTK IMAGE (PIL IMAGE) - pil giúp chuyển đổi ảnh từ mảng numpy thành 1 obj có thể thao tác được và ctk đọc được
#    pil_image = Image.fromarray(img_RGB)
#    #SCALE ẢNH VỀ KÍCH THƯỚC NHỎ HƠN ĐỂ HIỂN THỊ TRÊN GIAO DIỆN
#    pil_image.thumbnail((450,520))#chỉ thu nhỏ ảnh để hiển thị không thay đổi pixel gốc, nếu ảnh nhỏ hơn thì không scale
#    #PIL IMAGE SANG CTK IMAGE - chuyển đổi ảnh từ định dạng PIL sang định dạng ảnh của ctk (chủ yếu để hiển thị trên giao diện)
#    source_ctk_image = ctk.CTkImage( 
#        light_image=pil_image,#lúc ở dark mode thì hiển thị ảnh này, còn light mode thì hiển thị ảnh khác
#        dark_image=pil_image,
#        size=pil_image.size#hiển thị ảnh theo kích thước của ảnh gốc, không scale thêm nữa
#    )
#    #HIỂN THỊ
#    image_canvas.configure(#đưa ảnh vào label hiển thị (thảy đổi configure của label)
#        image=source_ctk_image,
#        text=""
#    )
    #GỌI LẠI HÀM KHÔNG CẦN CODE NHƯ TRÊN
    display_source_image()
#CẬP NHẬT STATUS# thay đổi status label khi mở ảnh thành công
    status_label.configure(text="● Đã mở ảnh"
                           , text_color="#22C55E"
                           , fg_color="#0F172A")
    print(
        "Ảnh từ file:",
        original_img.shape
    )
    # Đóng cửa sổ chọn nguồn
    dialog.destroy()
#thiết lập grid cho các widgets con bên trong slidebar

def show_loading_overlay(text):
    app.update_idletasks()

    overlay = ctk.CTkToplevel(app)
    overlay.overrideredirect(True)
    overlay.transient(app)

    try:
        overlay.attributes("-alpha", 0.88)
    except:
        pass

    x = app.winfo_rootx()
    y = app.winfo_rooty()
    width = app.winfo_width()
    height = app.winfo_height()
    overlay.geometry(f"{width}x{height}+{x}+{y}")

    # Canvas phủ lên app trong lúc camera đang khởi động
    loading_canvas = Canvas(
        overlay,
        width=width,
        height=height,
        bg=COLOR_BG,
        highlightthickness=0
    )
    loading_canvas.pack(fill="both", expand=True)

    center_x = width / 2
    center_y = height / 2

    loading_canvas.create_rectangle(
        center_x - 150,
        center_y - 60,
        center_x + 150,
        center_y + 60,
        fill=COLOR_NAVY,
        outline=COLOR_BORDER,
        width=1
    )

    loading_canvas.create_text(
        center_x,
        center_y,
        text=text,
        fill=COLOR_TEXT,
        font=("Segoe UI", 18, "bold")
    )

    overlay.grab_set()
    overlay.lift()
    overlay.update()

    return overlay
def close_loading_overlay(overlay):
    if overlay is not None and overlay.winfo_exists():
        try:
            overlay.grab_release()
        except:
            pass
        overlay.destroy()


#LÁY TỪ CAMERA
def open_camera(dialog):
    global camera, camera_after_id, camera_ctk_image, camera_frame
    dialog.destroy()
    camera_frame = None
    camera_after_id = None
    #lớp overlay trong lúc load cam
    loading_overlay = show_loading_overlay("Đang mở camera...")

    def start_camera():
        global camera, camera_after_id, camera_ctk_image, camera_frame

        camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        close_loading_overlay(loading_overlay)

        #Tạo của sổ để hiển thị cam
        camera_window = ctk.CTkToplevel(app)
        camera_window.title("Camera")
        camera_window.geometry("800x650")
        camera_window.configure(fg_color=COLOR_BG)
        camera_window.transient(app)
        camera_window.grab_set()#khóa không cho tương tác với của sổ ngoài

        camera_title = ctk.CTkLabel(
            camera_window,
            text="Chụp ảnh tài liệu của bạn",
            font=("Segoe UI", 22, "bold"),
            text_color=COLOR_TEXT
        )
        camera_title.pack(
            pady=(15, 10)
        )

        #preview cam
        camera_label = ctk.CTkLabel(
            camera_window,
            text="Đang mở camera...",
            width=700,
            height=480,
            fg_color="#0D1324",
            corner_radius=10,
            text_color=COLOR_TEXT_MUTED
        )
        camera_label.pack(
            padx=20,
            pady=10,
            expand=True,
            fill="both"
        )

        #CẬP NHẬT FRAME (camera lấy liên tục frame by frame)
        def update_camera():
            global camera_frame, camera_ctk_image, camera_after_id
            if camera is None:
                return

            ret, frame = camera.read()
            if ret:
                camera_frame = frame.copy()

                frame_rgb = cv2.cvtColor(
                    frame,
                    cv2.COLOR_BGR2RGB
                )
                pil_frame = Image.fromarray(
                    frame_rgb
                )
                pil_frame.thumbnail(
                    (700, 480)
                )
                camera_ctk_image = ctk.CTkImage(
                    light_image=pil_frame,
                    dark_image=pil_frame,
                    size=pil_frame.size
                )
                camera_label.configure(
                    image=camera_ctk_image,
                    text=""
                )
                camera_label.image = camera_ctk_image

            camera_after_id = camera_window.after(
                15,
                update_camera
            )

        #CHỤP ẢNH (NGƯỜI DÙNG THAO TÁC CHỤP)
        def capture_image():
            global original_img,input_img
            if camera_frame is None:
                print("Chưa nhận được ảnh chụp!")
                return

            input_img = camera_frame.copy()
            original_img = input_img.copy()
            clear_old_document_state()
            reset_view()
#           img_rgb = cv2.cvtColor(
#                original_img,
#                cv2.COLOR_BGR2RGB
#            )
#            pil_image = Image.fromarray(
#                img_rgb
#            )
#            pil_image.thumbnail((450, 520))
#            source_ctk_image = ctk.CTkImage(
#                light_image=pil_image,
#                dark_image=pil_image,
#                size=pil_image.size
#            )
#            image_canvas.configure(
#                image=source_ctk_image,
#                text=""
#            )
#            image_canvas.image = source_ctk_image
#            print("Ảnh Camera", original_img.shape)
            close_camera()

        #HÀM ĐÓNG CAM
        def close_camera():
            global camera, camera_after_id
            if camera_after_id is not None:
                try:
                    camera_window.after_cancel(
                        camera_after_id
                    )
                except:
                    pass
                camera_after_id = None

            if camera is not None:
                camera.release()
                camera = None

            camera_window.destroy()

        # TẠO FRAME CHỨA BUTTON
        button_frame = ctk.CTkFrame(
            camera_window,
            fg_color="transparent"
        )
        button_frame.pack(
            pady=(5, 20)
        )

        # NÚT CHỤP
        capture_button = ctk.CTkButton(
            button_frame,
            text="Chụp ảnh",
            width=160,
            height=42,
            fg_color=COLOR_PURPLE,
            hover_color=COLOR_PURPLE_HOVER,
            command=capture_image
        )
        capture_button.pack(
            side="left",
            padx=10
        )

        # NÚT HỦY
        close_button = ctk.CTkButton(
            button_frame,
            text="Hủy",
            width=120,
            height=42,
            fg_color=COLOR_NAVY_LIGHT,
            hover_color="#202D4A",
            border_width=1,
            border_color=COLOR_BORDER,
            command=close_camera
        )
        close_button.pack(
            side="left",
            padx=10
        )

        camera_window.protocol(
            "WM_DELETE_WINDOW",
            close_camera
        )

        if not camera.isOpened():
            camera_label.configure(text="Không thể mở Camera!")
            capture_button.configure(state="disabled")
            return

        update_camera()

    app.after(100, start_camera)
    
#----HÀM MỞ CỬA SỔ CHỌN NGUỒN ẢNH----
def open_source_dialog():
    dialog = ctk.CTkToplevel(app)
    dialog.title("Chọn nguồn ảnh")
    dialog.geometry("300x260")
    dialog.resizable(False, False)
    dialog.configure(fg_color=COLOR_NAVY)
    dialog.transient(app)  # Đặt cửa sổ con trên cửa sổ chính
    dialog.grab_set()  # Ngăn người dùng tương tác với cửa sổ chính
    title = ctk.CTkLabel(
        dialog,
        text="Chọn nguồn tài liệu",
        font=("Segoe UI", 20, "bold"),
        text_color=COLOR_TEXT
    )
    title.pack(pady=10)
    #tạo 2 button con
    #Button chọn file
    file_button = ctk.CTkButton(
        dialog
        ,text="Nhập từ file"
        ,height=42
        ,fg_color=COLOR_PURPLE
        ,hover_color=COLOR_PURPLE_HOVER
        ,command=lambda: choose_file(dialog)
    )
    file_button.pack(fill="x"
                     , padx=35
                     , pady=6)
    
    #Button chụp ảnh
    camera_button = ctk.CTkButton(
        dialog
        ,text="Chụp từ camera"
        ,height=42
        ,fg_color=COLOR_NAVY_LIGHT
        ,hover_color="#202D4A"
        ,border_width=1
        ,border_color=COLOR_BORDER
        ,command=lambda: open_camera(dialog)
    )

    camera_button.pack(fill="x"
                       , padx=35
                       , pady=6)
    cancel_button = ctk.CTkButton(
        dialog
        ,text="Hủy"
        ,height=32
        ,fg_color="transparent"
        ,hover_color=COLOR_NAVY_LIGHT
        ,text_color=COLOR_TEXT_MUTED
        ,command=dialog.destroy
    )
    cancel_button.pack(
        pady=(12, 0)
    )

        
#----SIDEBAR        
#tạo label "Input" ở đầu slidebar
input_title = ctk.CTkLabel(sidebar
                           , text="Input"
                           , font=ctk.CTkFont(size=20, weight="bold")
                           , text_color=COLOR_TEXT)

input_title.pack(#nên dùng pack cho các widgets con bên trong slidebar, vì slidebar có width cố định
    anchor="w" #bám trái
    , padx=20
    , pady=(0, 8)
)
#nút mở ảnh
source_button = ctk.CTkButton(sidebar
                                     , text= "Thêm tài liệu"
                                     , height=40
                                     , corner_radius=8
                                     , fg_color=COLOR_PURPLE
                                     , hover_color=COLOR_PURPLE_HOVER
                                     ,command=open_source_dialog )
source_button.pack(fill="x" 
                    ,padx=20
                    ,pady=5) 

#THANH VIEW ZOOM
separator_view = ctk.CTkFrame(#tạo khoảng chia giữa 2 elements
    sidebar,
    height=1,
    fg_color=COLOR_BORDER
)

separator_view.pack(
    fill="x",
    padx=20,
    pady=(25, 18)
)
#tiêu đề
zoom_title = ctk.CTkLabel(
    sidebar
    ,text="VIEW ZOOM"
    ,font=("Segoe UI", 11, "bold")
    ,text_color=COLOR_TEXT_MUTED
)
zoom_title.pack(
    anchor="w",
    padx=20
)
#Thanh trượt (2 thành phần số và thanh)
#phần số - giá trị
zoom_value_label = ctk.CTkLabel(
    sidebar,
    text="100%",
    font=("Consolas", 13, "bold"),
    text_color="#C084FC"
)

zoom_value_label.pack(
    anchor="w",
    padx=20,
    pady=(6, 0)
)
#phần slider
zoom_slider = ctk.CTkSlider(
    sidebar,
    from_=50,
    to=300,
    button_color=COLOR_PURPLE,
    button_hover_color="#C084FC",
    progress_color=COLOR_PURPLE,
    fg_color=COLOR_BORDER,
    command=lambda value:on_zoom_change(value)
)
zoom_slider.set(100)
zoom_slider.pack(
    fill="x",
    padx=20,
    pady=10
)
#NÚT CHỌN CORNERS
scan_separator = ctk.CTkFrame(
    sidebar,
    height=1,
    fg_color=COLOR_BORDER
)

scan_separator.pack(
    fill="x",
    padx=20,
    pady=(20, 15)
)


scan_title = ctk.CTkLabel(
    sidebar,

    text="DOCUMENT SCAN",

    font=(
        "Segoe UI",
        11,
        "bold"
    ),

    text_color=COLOR_TEXT_MUTED
)

scan_title.pack(
    anchor="w",
    padx=20,
    pady=(0, 8)
)
#NÚT RESET
#button của hàm reset
reset_view_button = ctk.CTkButton(
    sidebar,
    text="Reset View",
    height=34,
    fg_color=COLOR_NAVY_LIGHT,
    hover_color="#202D4A",
    border_width=1,
    border_color=COLOR_BORDER,
    command=lambda:reset_view()
)
reset_view_button.pack(
    fill="x",
    padx=20,
    pady=(4, 10)
)

#NÚT CHỌN 4 GÓC
corner_button = ctk.CTkButton(
    sidebar,

    text="Chọn các góc",

    height=38,

    fg_color=COLOR_NAVY_LIGHT,

    hover_color="#202D4A",

    border_width=1,

    border_color=COLOR_BORDER,

    command=lambda:start_corner_selection()
)

corner_button.pack(
    fill="x",
    padx=20,
    pady=4
)

scan_button = ctk.CTkButton(
    sidebar,

    text="Quét thử",

    height=38,

    fg_color=COLOR_PURPLE,

    hover_color=COLOR_PURPLE_HOVER,

    state="disabled",

    command=lambda:preview_scan()
)

scan_button.pack(
    fill="x",
    padx=20,
    pady=4
)
#CÁC NÚT CHO MẢNH 1 (xử lý rotate và réize)
process_separator = ctk.CTkFrame(
    sidebar,
    height=1,
    fg_color=COLOR_BORDER
)
process_separator.pack(
    fill="x",
    padx=20,
    pady=(20, 15)
)
process_title = ctk.CTkLabel(
    sidebar,
    text="IMAGE PROCESSING",
    font=("Segoe UI", 11, "bold"),
    text_color=COLOR_TEXT_MUTED
)
process_title.pack(
    anchor="w",
    padx=20
)
#rotate
rotate_value_label = ctk.CTkLabel(
    sidebar,
    text="0°",
    font=("Consolas", 13, "bold"),
    text_color="#A78BFA"
)
rotate_value_label.pack(
    anchor="w",
    padx=20,
    pady=(10, 0)
)

rotate_slider = ctk.CTkSlider(
    sidebar,
    from_=-180,
    to=180,
    button_color=COLOR_PURPLE,
    progress_color=COLOR_PURPLE,
    fg_color=COLOR_BORDER,

    # vì hàm nằm phía dưới code
    command=lambda value: on_rotate_change(value)
)
rotate_slider.set(0)

rotate_slider.pack(
    fill="x",
    padx=20,
    pady=8
)
#resize
resize_value_label = ctk.CTkLabel(
    sidebar,
    text="100%",
    font=("Consolas", 13, "bold"),
    text_color="#60A5FA"
)

resize_value_label.pack(
    anchor="w",
    padx=20,
    pady=(10, 0)
)

resize_slider = ctk.CTkSlider(
    sidebar,
    from_=25,
    to=200,
    button_color=COLOR_BLUE,
    progress_color=COLOR_BLUE,
    fg_color=COLOR_BORDER,

    command=lambda value: on_resize_change(value)
)
resize_slider.set(100)

resize_slider.pack(
    fill="x",
    padx=20,
    pady=8
)
method_title = ctk.CTkLabel(
    sidebar,
    text="Interpolation",
    font =("Segoe UI", 10, "bold"),
    text_color=COLOR_TEXT_MUTED
)

method_title.pack(
    anchor="w",
    padx=20,
    pady=(5, 2)
)
method_frame = ctk.CTkFrame(
    sidebar,
    fg_color="transparent"
)

method_frame.pack(
    fill="x",
    padx=20,
    pady=(0, 5)
)
radio_auto = ctk.CTkRadioButton(
    method_frame,
    text="Auto",
    variable=resize_method_var,
    value="AUTO",
    command=lambda: on_method_change()
)

radio_auto.grid(
    row=0,
    column=0,
    sticky="w",
    pady=3
)


radio_nearest = ctk.CTkRadioButton(
    method_frame,
    text="Nearest",
    variable=resize_method_var,
    value="NEAREST",
    command=lambda: on_method_change()
)

radio_nearest.grid(
    row=1,
    column=0,
    sticky="w",
    pady=3
)


radio_linear = ctk.CTkRadioButton(
    method_frame,
    text="Linear",
    variable=resize_method_var,
    value="LINEAR",
    command=lambda: on_method_change()
)

radio_linear.grid(
    row=2,
    column=0,
    sticky="w",
    pady=3
)


radio_cubic = ctk.CTkRadioButton(
    method_frame,
    text="Cubic",
    variable=resize_method_var,
    value="CUBIC",
    command=lambda: on_method_change()
)

radio_cubic.grid(
    row=3,
    column=0,
    sticky="w",
    pady=3
)


radio_area = ctk.CTkRadioButton(
    method_frame,
    text="Area",
    variable=resize_method_var,
    value="AREA",
    command=lambda: on_method_change()
)

radio_area.grid(
    row=4,
    column=0,
    sticky="w",
    pady=3
)
method_label = ctk.CTkLabel(
    sidebar,
    text="Using: Original",
    font=("Consolas", 10),
    text_color=COLOR_TEXT_MUTED
)

method_label.pack(
    anchor="w",
    padx=20,
    pady=(0, 6)
)
#apply button
apply_preprocess_button = ctk.CTkButton(
    sidebar,

    text="Áp dụng",

    height=38,

    fg_color=COLOR_BLUE,
    hover_color="#1D4ED8",

    command=lambda: apply_preprocessing()
)

apply_preprocess_button.pack(
    fill="x",
    padx=20,
    pady=(6, 10)
)
#khoảng trắng
save_separator = ctk.CTkFrame(
    sidebar,
    height=1,
    fg_color=COLOR_BORDER
)

save_separator.pack(
    fill="x",
    padx=20,
    pady=(15, 12)
)
#nút lưu
save_button = ctk.CTkButton(
    sidebar,

    text="Lưu kết quả",

    height=40,

    fg_color="#16A34A",
    hover_color="#15803D",
    state="disabled",
    command=lambda: save_result()
)

save_button.pack(
    fill="x",
    padx=20,
    pady=4
)
#tạo doc mới
new_document_button = ctk.CTkButton(
    sidebar,
    text="Tài liệu mới",
    height=36,
    fg_color=COLOR_NAVY_LIGHT,
    hover_color="#202D4A",
    border_width=1,
    border_color=COLOR_BORDER,
    command=lambda: reset_all()
)

new_document_button.pack(
    fill="x",
    padx=20,
    pady=(4, 10)
)
#------------
#----CÁC HÀM THAO TÁC VỚI ẢNH
#------------    
#ẢNH GỐC
#----HÀM ZOOM----
def on_zoom_change(value):
    global zoom_scale
    #đưa percent zoom vể trục số
    percent = int(float(value))
    zoom_scale = percent /100
    #cập nhật số hiển thị
    zoom_value_label.configure(
            text=f"{percent}%"
    )
    #Hiển thị lại ảnh
    if original_img is not None:
        display_source_image()
#HÀM ĐẺ RESET VỀ HIỂN THỊ MẶC ĐỊNH
def reset_view():
    global zoom_scale, pan_y, pan_x
    #reset zoom
    zoom_scale = 1.0
    
    #reset pan
    pan_x = 0
    pan_y = 0
    
    zoom_slider.set(100)
    zoom_value_label.configure(
        text="100%"
    )
    if original_img is not None:
        display_source_image()
        

#----HÀM PAN----
def start_pan(event):
    global is_panning, pan_last_x,pan_last_y
    if original_img is None:
        return
    
    is_panning = True #đang giữ chuột
    #thì ghi nhớ vị trí chuột
    pan_last_x = event.x#lấy tọa độ
    pan_last_y = event.y
    #đổi cursor (hình dạng của con trỏ)
    image_canvas.configure(
    cursor="fleur"
    )
#kéo pan (giữ chuột)
def drag_pan(event):
    global pan_x,pan_y,pan_last_y,pan_last_x
    
    if not is_panning:
        return
    #tính xem đã di chuyển chuột bao nhiêu so với trc đó
    dx = event.x  - pan_last_x
    dy = event.y - pan_last_y
    
    #cộng chênh lệc dx,dy đó vào vị trí pan
    pan_x +=dx
    pan_y +=dy
    
    #Cập nhật lại last pan
    pan_last_x = event.x
    pan_last_y = event.y
    
    #vẽ lại ảnh trên canvas
    display_source_image()
def end_pan(event): #thả chuột
    global is_panning
    is_panning = False
    image_canvas.configure(
        cursor="arrow"# mặc định
    )

#HÀM TÍNH TOÁN TỌA ĐỘ (thao tác trên ảnh gốc)
# (tọa độ chấm trên hình trả về trên canvas)
def image_to_canvas(image_x, image_y):
    canvas_x = (display_offset_x + image_x * display_scale)#offset = vị trí căn giữa + pan, ví dụ P = (1000,500) thì tính lại canvas sẽ là 250 và 200
    canvas_y = (display_offset_y + image_y * display_scale)
    return canvas_x, canvas_y
#tọa độ chấm trên canvas trả đúng về tọa độ trên ảnh
def canvas_to_image(canvas_x, canvas_y):
    if original_img is None:
        return
    if display_scale <=0:
        return None
    #nếu chuột ngoài ảnh
    if not is_point_on_image(canvas_x, canvas_y):
        return None
        
    image_x = (canvas_x - display_offset_x)/display_scale 
    image_y = (canvas_y - display_offset_y)/display_scale
    return image_x, image_y
#hàm kiểm tra số âm để loại những dot vo nghĩa(ngoài ảnh gốc)
def is_point_on_image(canvas_x, canvas_y):

    left = display_offset_x

    top = display_offset_y

    right = (
        display_offset_x
        +
        display_width
    )

    bottom = (
        display_offset_y
        +
        display_height
    )


    return (
        left <= canvas_x <= right
        and
        top <= canvas_y <= bottom
    )
    
#MOUSE ZOOM (hàm zoom bằng chuột)
def mouse_wheel_zoom(event):

    global zoom_scale,pan_x, pan_y
    if original_img is None:
        return
#xem chuột có nằm trên ảnh?
    if not is_point_on_image(
        event.x,
        event.y
    ):
        return
#lưu lại pixel đang nằm dưới chuột
    point = canvas_to_image(
        event.x,
        event.y
    )
    if point is None:
        return
    image_x, image_y = point
#xác định thao tác là zoom in hay out
    if event.delta > 0:
        new_zoom = zoom_scale * 1.1
    else:
        new_zoom = zoom_scale / 1.1
#đặt giới hạn zoom
    new_zoom = max(
        0.5,
        min(3.0, new_zoom)
    )
    if abs(new_zoom - zoom_scale) < 0.0001:
        return
    #cập nhật tọa độ zoom
    zoom_scale = new_zoom
    #tính hiển thị trên displya mới
    new_display_scale = (
        fit_scale * zoom_scale
    )
    # lấy kích thước canvas
    canvas_width = image_canvas.winfo_width()
    canvas_height = image_canvas.winfo_height()
    # kích thước ảnh mới sau zoom
    img_height, img_width = original_img.shape[:2]
    new_display_width = (img_width * new_display_scale)
    new_display_height = (img_height * new_display_scale )
    #vị trí mới sau zoom
    center_offset_x = (canvas_width - new_display_width) / 2
    center_offset_y = (canvas_height - new_display_height) / 2
    desired_offset_x = (event.x - image_x * new_display_scale)
    desired_offset_y = (event.y - image_y * new_display_scale)
    pan_x = (desired_offset_x - center_offset_x)
    pan_y = ( desired_offset_y - center_offset_y)
    percent = int(zoom_scale * 100)
    zoom_slider.set(percent)
    zoom_value_label.configure(
        text=f"{percent}%"
    )
    display_source_image()
#HÀM LẤY TỌA ĐỘ 4 GÓC (trên canvas)
def start_corner_selection():
    global current_corners
    global corner_select_mode
    if original_img is None:
        print(
            "Hãy thêm tài liệu!"
        )
        return
    current_corners = []
    corner_select_mode = True
    scan_button.configure( state= "disabled")
    status_label.configure(
        text="● Chọn góc 1/4"
    )
    display_source_image()
#ĐƯA ẢNH TỪ CLICK TRÊN CANVAS VỀ TỌA ĐỘ THẬT 
def add_corner(event):
    global current_corners
    global corner_select_mode
    
    if not corner_select_mode:
        return
    #click vô point cũ thì xóa
    point_index = find_corner_at(
        event.x,
        event.y
    )
    if point_index is not None:
        current_corners.pop(
            point_index
        )
        if len(current_corners) < 4:
            #dùng mảnh 2 sắp xếp
            scan_button.configure(
                state = "disabled"
            )
        else:
            scan_button.configure(
                        state = "normal"
                    )
            status_label.configure(
                text=(
                    f"● Đã chọn"
                    f"{len(current_corners)} điểm"
                )
            )
        display_source_image()
        return

    point = canvas_to_image(
        event.x,
        event.y
    )
    if point is None:
        return
    image_x, image_y = point
    current_corners.append([
        image_x,
        image_y
    ])
    if len(current_corners) >= 4:
        scan_button.configure(
            state="normal"
        )
    else:
        scan_button.configure(
            state="disabled"
        )
    status_label.configure(
        text=(
            f"● Đã chọn "
            f"{len(current_corners)} điểm"
        )
    )
    display_source_image()
    
#TẤM CANVAS ĐỂ NGƯỜI DÙNG BIẾT TRƯỚC ĐANG CHỌN NTN
#def draw_scan_overlay():
#    if len(current_corners) == 0:
#        return
#    points_canvas = []
#    for image_x, image_y in current_corners:
#        canvas_x, canvas_y = image_to_canvas(
#            image_x,
#            image_y
#        )
#        points_canvas.append(
#            (canvas_x, canvas_y)
#        )
#    if 2 <= len(points_canvas) < 4:
#
#        coords = []
#
#        for x, y in points_canvas:
#
#            coords.extend(
#                [x, y]
#            )
#        image_canvas.create_line(
#            *coords,
#            fill="#22C55E",
#            width=3,
#            tags="corner_overlay"
#        )
#    if len(points_canvas) == 4:
#        coords = []
#        for x, y in points_canvas:
#            coords.extend(
#                [x, y]
#            )
#        image_canvas.create_polygon(
#            *coords,
#            fill="",
#            outline="#22C55E",
#            width=3,
#            tags="corner_overlay"
#        )
#    radius = 7
#    for index, (x, y) in enumerate(
#        points_canvas
#    ):
#        image_canvas.create_oval(
#            x - radius,
#            y - radius,
#            x + radius,
#            y + radius,
#            fill="#22C55E",
#            outline="white",
#            width=2,
#            tags="corner_overlay"
#        )
#        image_canvas.create_text(
#            x,
#            y - 18,
#            text=f"P{index + 1}",
#            fill="white",
#            tags="corner_overlay"
#        )     
def draw_scan_overlay():
    if len(current_corners) == 0:
        return
    # =========================================
    # TRƯỜNG HỢP CHƯA ĐỦ 4 ĐIỂM
    # Chỉ hiện các điểm người dùng vừa chọn
    # =========================================

    if len(current_corners) < 4:

        for index, (image_x, image_y) in enumerate(
            current_corners
        ):

            canvas_x, canvas_y = image_to_canvas(
                image_x,
                image_y
            )

            draw_scan_point(
                canvas_x,
                canvas_y,
                index + 1,
                "#22C55E"
            )

        return


    # =========================================
    # TỪ 4 ĐIỂM TRỞ LÊN
    # Nhờ Mảnh 2 xác định 4 góc ngoài
    # =========================================

    outer_rect, pt_ML, pt_MR = smart_sort_points(
        current_corners
    )


    # =========================================
    # VẼ KHUNG 4 GÓC NGOÀI
    # =========================================

    outer_canvas = []

    for image_x, image_y in outer_rect:

        canvas_x, canvas_y = image_to_canvas(
            image_x,
            image_y
        )

        outer_canvas.extend(
            [canvas_x, canvas_y]
        )


    image_canvas.create_polygon(
        *outer_canvas,

        fill="",
        outline="#22C55E",
        width=3,

        tags="scan_overlay"
    )


    # =========================================
    # VẼ TẤT CẢ ĐIỂM
    # =========================================

    for index, (image_x, image_y) in enumerate(
        current_corners
    ):

        canvas_x, canvas_y = image_to_canvas(
            image_x,
            image_y
        )


        # kiểm tra điểm này có phải
        # một trong 4 góc ngoài không
        is_outer = False

        for corner in outer_rect:

            distance = np.linalg.norm(
                np.array(
                    [image_x, image_y]
                )
                -
                corner
            )

            if distance < 1:
                is_outer = True
                break


        # =============================
        # GÓC NGOÀI
        # =============================

        if is_outer:

            color = "#22C55E"


        # =============================
        # ĐIỂM NẾP GẤP
        # =============================

        else:

            color = "#FACC15"


        draw_scan_point(
            canvas_x,
            canvas_y,
            index + 1,
            color
        )
def draw_scan_point(
    x,
    y,
    number,
    color
):

    radius = 7


    image_canvas.create_oval(

        x - radius,
        y - radius,

        x + radius,
        y + radius,

        fill=color,
        outline="white",
        width=2,

        tags="scan_overlay"
    )


    image_canvas.create_text(

        x,
        y - 18,

        text=f"P{number}",

        fill="white",

        tags="scan_overlay"
    )
def find_corner_at(canvas_x, canvas_y):
    # bán kính bắt chuột lớn hơn bán kính dot
    hit_radius = 18

    for index, (image_x, image_y) in enumerate(
        current_corners
    ):
        # tọa độ ảnh thật → Canvas
        corner_x, corner_y = image_to_canvas(
            image_x,
            image_y
        )
        dx = canvas_x - corner_x
        dy = canvas_y - corner_y

        distance_squared = (
            dx * dx
            +
            dy * dy
        )
        if distance_squared <= hit_radius ** 2:

            return index
    return None
#HÀM CHO PHÉP KÉO CHỈNH 4 GÓC
def drag_corner(event):
    global current_corners, dragging_corner
    if dragging_corner is None:
        return
    # Canvas → tọa độ ảnh thật
    point = canvas_to_image(
        event.x,
        event.y
    )
    # nếu kéo chuột ra ngoài ảnh
    if point is None:
        return
    image_x, image_y = point
    # cập nhật đúng corner đang kéo
    current_corners[dragging_corner] = [
        image_x,
        image_y
    ]
    # vẽ lại ảnh + polygon
    display_source_image()
#GỬI 4 GÓC SANG MẢNH 2 để lấy về ảnh preview
#tính toán lại vị trí 4 góc để hiển thị đẹp nhất
#def calculate_output_size(corners):
#    # Sắp xếp 4 điểm theo:
#    # TL, TR, BR, BL
#    rect = order_points(
#        np.array(
#            corners,
#            dtype="float32"
#        )
#    )
#    tl, tr, br, bl = rect
#    # TÍNH CHIỀU RỘNG
#    width_top = np.linalg.norm( tr - tl )
#    width_bottom = np.linalg.norm( br - bl )
#    output_width = int(
#        max( width_top, width_bottom)
#    )
#    # TÍNH CHIỀU CAO
#    height_left = np.linalg.norm( bl - tl )
#    height_right = np.linalg.norm( br - tr )
#    output_height = int(
#        max( height_left, height_right)
#    )
#    # tránh trường hợp bằng 0
#    output_width = max( 1, output_width)
#    output_height = max( 1, output_height
#    )
#    return (
#        output_width,
#        output_height
#    )
#
def preview_scan():
    global scan_img
    global result_img
    if original_img is None:
        print("Chưa có ảnh")
        return
    if len(current_corners) < 4:
        print("Chọn ít nhất 4 điểm")
        return
    # MẢNH 2
    scan_img = process_scanned_image(
        original_img,
        current_corners
    )
    if scan_img is None:
        print(
            "Không thể tạo ảnh Preview!"
        )
        return
    # Result ban đầu = Scan
    result_img = scan_img.copy()
    reset_result_view()
    save_button.configure(
        state="normal"
    )
    status_label.configure(
        text="● Đã tạo Preview",
        text_color="#C4B5FD",
        fg_color="#312E81"
    )
def reset_result_view():

    global result_zoom_scale

    global result_pan_x
    global result_pan_y


    result_zoom_scale = 1.0

    result_pan_x = 0
    result_pan_y = 0


    if result_img is not None:

        display_result_image()
#ẢNH KẾT QUẢ
def display_result_image():#luồng tương tự ảnh gốc

    global result_photo
    global result_fit_scale
    global result_display_scale

    global result_display_width
    global result_display_height

    global result_offset_x
    global result_offset_y


    if result_img is None:
        return
    result_canvas.update_idletasks()
    canvas_width = result_canvas.winfo_width()
    canvas_height = result_canvas.winfo_height()
    if canvas_width <= 1 or canvas_height <= 1:
        return

    img_height, img_width = result_img.shape[:2]


    scale_width = canvas_width / img_width
    scale_height = canvas_height / img_height

    result_fit_scale = min(
        scale_width,
        scale_height
    )
    result_display_scale = (
        result_fit_scale
        *
        result_zoom_scale
    )
    result_display_width = max(
        1,
        int(img_width * result_display_scale)
    )
    result_display_height = max(
        1,
        int(img_height * result_display_scale)
    )
    result_offset_x = (
        canvas_width
        -
        result_display_width
    ) / 2 + result_pan_x
    result_offset_y = (
        canvas_height
        -
        result_display_height
    ) / 2 + result_pan_y
    img_rgb = cv2.cvtColor(
        result_img,
        cv2.COLOR_BGR2RGB
    )
    # NumPy → PIL
    pil_img = Image.fromarray(
        img_rgb
    )
    # Resize CHỈ ĐỂ HIỂN THỊ
    pil_img = pil_img.resize(
        (
            result_display_width,
            result_display_height
        ),

        Image.Resampling.LANCZOS
    )
    result_photo = ImageTk.PhotoImage(
        pil_img
    )

    result_canvas.delete("all")


    result_canvas.create_image(
        result_offset_x,
        result_offset_y,

        anchor="nw",

        image=result_photo
    )
#ZOOM BẰNG CHUỘT ẢNH RESULT
#kiểm tra coi chuột có ở trên ảnh result
def is_point_on_result(
    canvas_x,
    canvas_y
):
    left = result_offset_x
    top = result_offset_y
    right = (
        result_offset_x
        +
        result_display_width
    )
    bottom = (
        result_offset_y
        +
        result_display_height
    )
    return (
        left <= canvas_x <= right
        and
        top <= canvas_y <= bottom
    )
def result_canvas_to_image(
    canvas_x,
    canvas_y
):
    if result_img is None:
        return None
    if result_display_scale <= 0:
        return None
    if not is_point_on_result(
        canvas_x,
        canvas_y
    ):
        return None
    image_x = (
        canvas_x
        -
        result_offset_x
    ) / result_display_scale
    image_y = (
        canvas_y
        -
        result_offset_y
    ) / result_display_scale
    return image_x, image_y
def result_mouse_wheel_zoom(event):

    global result_zoom_scale
    global result_pan_x
    global result_pan_y


    if result_img is None:
        return


    if not is_point_on_result(
        event.x,
        event.y
    ):

        return


    # Pixel Result đang nằm dưới chuột
    point = result_canvas_to_image(
        event.x,
        event.y
    )


    if point is None:
        return


    image_x, image_y = point

    if event.delta > 0:

        new_zoom = (
            result_zoom_scale * 1.1
        )

    else:

        new_zoom = (
            result_zoom_scale / 1.1
        )


    # 50% → 400%
    new_zoom = max(
        0.5,
        min(4.0, new_zoom)
    )


    if abs(
        new_zoom
        -
        result_zoom_scale
    ) < 0.0001:

        return


    result_zoom_scale = new_zoom

    new_display_scale = (
        result_fit_scale
        *
        result_zoom_scale
    )


    canvas_width = (
        result_canvas.winfo_width()
    )

    canvas_height = (
        result_canvas.winfo_height()
    )


    img_height, img_width = (
        result_img.shape[:2]
    )


    new_width = (
        img_width
        *
        new_display_scale
    )


    new_height = (
        img_height
        *
        new_display_scale
    )


    # Center mới
    center_x = (
        canvas_width
        -
        new_width
    ) / 2


    center_y = (
        canvas_height
        -
        new_height
    ) / 2


    # Giữ pixel dưới chuột
    desired_x = (
        event.x
        -
        image_x * new_display_scale
    )


    desired_y = (
        event.y
        -
        image_y * new_display_scale
    )


    result_pan_x = (
        desired_x - center_x
    )


    result_pan_y = (
        desired_y - center_y
    )
    display_result_image()
#HÀM PAN
def start_result_pan(event):

    global result_is_panning
    global result_last_x
    global result_last_y


    if result_img is None:
        return


    result_is_panning = True


    result_last_x = event.x
    result_last_y = event.y


    result_canvas.configure(
        cursor="fleur"
    )
def result_mouse_wheel_zoom(event):

    global result_zoom_scale
    global result_pan_x
    global result_pan_y


    if result_img is None:
        return


    if not is_point_on_result(
        event.x,
        event.y
    ):

        return


    # Pixel Result đang nằm dưới chuột
    point = result_canvas_to_image(
        event.x,
        event.y
    )


    if point is None:
        return


    image_x, image_y = point


    # ===============================
    # ZOOM IN / OUT
    # ===============================

    if event.delta > 0:

        new_zoom = (
            result_zoom_scale * 1.1
        )

    else:

        new_zoom = (
            result_zoom_scale / 1.1
        )


    # 50% → 400%
    new_zoom = max(
        0.5,
        min(4.0, new_zoom)
    )

    if abs(
        new_zoom
        -
        result_zoom_scale
    ) < 0.0001:

        return

    result_zoom_scale = new_zoom

    new_display_scale = (
        result_fit_scale
        *
        result_zoom_scale
    )


    canvas_width = (
        result_canvas.winfo_width()
    )

    canvas_height = (
        result_canvas.winfo_height()
    )


    img_height, img_width = (
        result_img.shape[:2]
    )


    new_width = (
        img_width
        *
        new_display_scale
    )


    new_height = (
        img_height
        *
        new_display_scale
    )


    # Center mới
    center_x = (
        canvas_width
        -
        new_width
    ) / 2


    center_y = (
        canvas_height
        -
        new_height
    ) / 2


    # Giữ pixel dưới chuột
    desired_x = (
        event.x
        -
        image_x * new_display_scale
    )


    desired_y = (
        event.y
        -
        image_y * new_display_scale
    )


    result_pan_x = (
        desired_x - center_x
    )


    result_pan_y = (
        desired_y - center_y
    )


    display_result_image()
#kéo
def drag_result_pan(event):

    global result_pan_x
    global result_pan_y

    global result_last_x
    global result_last_y


    if not result_is_panning:
        return


    dx = (
        event.x - result_last_x
    )

    dy = (
        event.y - result_last_y
    )


    result_pan_x += dx
    result_pan_y += dy


    result_last_x = event.x
    result_last_y = event.y


    display_result_image()
#thả
def end_result_pan(event):

    global result_is_panning


    result_is_panning = False


    result_canvas.configure(
        cursor="arrow"
    )    
#TỰ RESIZE
def get_resize_model():

    selected_method = resize_method_var.get()


    # ==================================
    # AUTO - GUI TỰ QUYẾT ĐỊNH
    # ==================================

    if selected_method == "AUTO":

        if resize_scale < 1:

            return cv2.INTER_AREA

        elif resize_scale > 1:

            return cv2.INTER_CUBIC

        else:

            return cv2.INTER_LINEAR


    # ==================================
    # NGƯỜI DÙNG TỰ CHỌN
    # ==================================

    if selected_method == "NEAREST":

        return cv2.INTER_NEAREST


    elif selected_method == "LINEAR":

        return cv2.INTER_LINEAR


    elif selected_method == "CUBIC":

        return cv2.INTER_CUBIC


    elif selected_method == "AREA":

        return cv2.INTER_AREA


    # dự phòng
    return cv2.INTER_LINEAR
def update_method_label():

    selected_method = resize_method_var.get()


    # Không resize
    if resize_scale == 1.0:

        method_label.configure(
            text="Using: Original"
        )

        return


    # ==========================
    # AUTO
    # ==========================

    if selected_method == "AUTO":

        if resize_scale < 1:

            method_label.configure(
                text="Auto → INTER_AREA"
            )

        else:

            method_label.configure(
                text="Auto → INTER_CUBIC"
            )

        return


    # ==========================
    # MANUAL
    # ==========================

    method_label.configure(
        text=f"Manual → INTER_{selected_method}"
    )
def on_result_resize(event):

    if result_img is not None:

        display_result_image()
#MẢNH 1: Hàm xoay ảnh       
def on_rotate_change(value):

    global rotate_angle

    rotate_angle = int(
        float(value)
        )

    rotate_value_label.configure(
        text=f"{rotate_angle}°"
    )    
    #update ngay
    update_output_preview()
    
#Hàm resize 
def on_resize_change(value):

    global resize_scale


    percent = int(
        float(value)
    )

    resize_scale = (
        percent / 100
    )


    resize_value_label.configure(
        text=f"{percent}%"
    )


    # cập nhật method đang dùng
    update_method_label()


    # preview realtime
    update_output_preview()
def on_method_change():

    update_method_label()

    update_output_preview()
def apply_preprocessing():
    global result_img
    if scan_img is None:
        print("Hãy Quét thử trước!")
        return
    
    # LUÔN LẤY ẢNH SAU MẢNH 2 LÀM GỐC
    processed_img = scan_img.copy()
    # MẢNH 1 - ROTATE
    if rotate_angle != 0:

        processed_img = rotation_pic(
            processed_img,
            rotate_angle
        )
    # GUI CHỌN INTERPOLATION
    if resize_scale < 1:

        model = get_resize_model()

    elif resize_scale > 1:

        model = get_resize_model()

    else:

        model = get_resize_model()
    # MẢNH 1 - RESIZE ẢNH THẬT
    if resize_scale != 1.0:
        processed_img = zoom_pic(
            processed_img,
            scale=resize_scale,
            model=model
        )

    result_img = processed_img
    # chỉ reset cách nhìn Result
    reset_result_view()
    status_label.configure(
        text="● Đã áp dụng Rotate / Resize",
        text_color="#C4B5FD",
        fg_color="#312E81"
    )
    print(
        "Result:",
        result_img.shape
    )
#MẢNH 1 HÀM PREVIEW CHUNG CHO 2 THUỘC TÍNH
def update_output_preview():

    global result_img


    if scan_img is None:
        return


    # luôn xử lý từ ảnh Scan ban đầu
    processed_img = scan_img.copy()


    # =============================
    # ROTATE - MẢNH 1
    # =============================

    if rotate_angle != 0:

        processed_img = rotation_pic(
            processed_img,
            rotate_angle
        )


    # =============================
    # MODEL RESIZE
    # =============================

    model = get_resize_model()


    # =============================
    # RESIZE - MẢNH 1
    # =============================

    if resize_scale != 1.0:

        processed_img = zoom_pic(
            processed_img,
            scale=resize_scale,
            model=model
        )


    result_img = processed_img


    display_result_image()
#----WORKSPACE----
#thiết lập workspace
workspace = ctk.CTkFrame( app ,#workspace là con của app
                        corner_radius=0
                        , fg_color=COLOR_NAVY_LIGHT)

#thiết lập grid cho workspace
workspace.grid(row=0, column=1, sticky="nsew")
workspace.grid_columnconfigure(0, weight=1)
workspace.grid_rowconfigure(0, weight=0) 
workspace.grid_rowconfigure(1, weight=1)  
workspace.grid_columnconfigure(1, weight=1)
#xây dụng các widgets con bên trong workspace
#HEADER
header = ctk.CTkFrame(workspace
                     , fg_color=COLOR_NAVY)
header.grid(row=0
            , column=0
            ,columnspan=2
            , sticky="nsew"
            ,padx = 25
            ,pady = (20,10))
#tilte label
workspace.title = ctk.CTkLabel(header
                               , text="Scanner Document"
                                ,font=("Segoe UI", 24, "bold")
                                ,text_color=COLOR_TEXT)
workspace.title.pack(anchor="w"
                     ,side = "left")
#trạng thái
status_label = ctk.CTkLabel(
    header
    ,text="● Sẵn sàng"
    ,height=30
    ,corner_radius=15
    ,fg_color="#172554"
    ,text_color="#93C5FD"
    ,font=("Segoe UI", 11, "bold")
)
status_label.pack(
    side="right"
)
#Khung ảnh
#ảnh source
image_frame_source = ctk.CTkFrame(workspace
                           , fg_color=COLOR_NAVY_LIGHT
                           ,corner_radius=12
                           ,border_width=1
                           ,border_color=COLOR_BORDER
                           )

image_frame_source.grid(row=1
                 , column=0
                 ,padx=25
                 ,pady=(10,25)
                 ,sticky="nsew")

image_title_source  = ctk.CTkLabel(image_frame_source
                            , text="Ảnh tài liệu gốc"
                            ,font=("Segoe UI", 12, "bold")
                            ,text_color=COLOR_TEXT_MUTED)
image_title_source.pack(anchor="w"
                  ,side = "top"
                  ,padx=16
                  ,pady=(16,0))

#image_label_source = ctk.CTkLabel(
#    image_frame_source,
#    image=source_ctk_image,
#    text="Chưa có tài liệu\n\nMở ảnh hoặc sử dụng Camera",
#    fg_color="#0D1324",
#    corner_radius=8,
#    text_color=COLOR_TEXT_MUTED
#)
#image_label_source.pack(
#    expand=True,
#    fill="both",
#
#    padx=16,
#    pady=(0, 16)
#)
image_canvas = tk.Canvas(#DÙNG CANVAS ĐỂ CÓ THỂ THAO TÁC VỚI ẢNH
    image_frame_source,
    bg="#0D1324",
    highlightthickness=0
)

image_canvas.pack(
    expand=True,
    fill="both",
    padx=16,
    pady=(10, 16)
)

#ảnh ra
image_frame_result = ctk.CTkFrame(workspace
                           , fg_color=COLOR_NAVY_LIGHT
                           ,corner_radius=12
                           ,border_width=1
                           ,border_color=COLOR_BORDER
                           )

image_frame_result.grid(row=1
                 , column=1
                 ,padx=25
                 ,pady=(10,25)
                 ,sticky="nsew")

result_header = ctk.CTkFrame(
    image_frame_result,
    fg_color="transparent"
)
result_header.pack(
    fill="x",
    padx=16,
    pady=(12, 5)
)
image_title_result = ctk.CTkLabel(
    result_header,

    text="Ảnh tài liệu đã xử lý",

    font=(
        "Segoe UI",
        12,
        "bold"
    ),

    text_color=COLOR_TEXT_MUTED
)

image_title_result.pack(
    side="left"
)
result_reset_button = ctk.CTkButton(
    result_header,

    text="Reset View",

    width=90,
    height=28,

    fg_color=COLOR_NAVY,

    hover_color=COLOR_NAVY_LIGHT,

    command=reset_result_view
)

result_reset_button.pack(
    side="right"
)
result_canvas = tk.Canvas(
    image_frame_result,
    bg="#0D1324",
    highlightthickness=0
)
result_canvas.pack(
    expand=True,
    fill="both",
    padx=16,
    pady=(10, 16)
)
#DÙNG HÀM ĐỂ ẢNH TỰ SCALE THEO CANVAS
def on_canvas_resize(event):

    if original_img is not None:

        display_source_image()
        
#BIND SỰ KIỆN
#-----ẢNH GỐC----
#thêm tác vụ cho chuột trái
def on_left_press(event):
    global dragging_corner
    if corner_select_mode:
        add_corner(event)
        return
    corner_index = find_corner_at(
        event.x
        , event.y
    )
    if corner_index is not None:
        dragging_corner = corner_index
        image_canvas.configure(
            cursor="hand2"
        )
        return
#Chặn pan khi đang chọn góc
def on_left_drag(event):
    if corner_select_mode:
        return
    if dragging_corner is not None:
        drag_corner(event)
        return
#Mouse release
def on_left_release(event):
    global dragging_corner
    if dragging_corner is not None:

        dragging_corner = None

        image_canvas.configure(
            cursor="arrow"
        )

        return
    
#HÀM LÀM VIỆC VỚI CHUỘT TRÁI
def on_right_press(event):
    start_pan(event)
def on_right_drag(event):
    drag_pan(event)
def on_right_release(event):
    end_pan(event)
#BIND
image_canvas.bind(
    "<B1-Motion>",
    on_left_drag
)        
#zoom        
image_canvas.bind(
    "<Configure>"#sự kiên xảy ra khi thay đổi kích thước vị trí (phóng to thu nhỏ cửa sổ)
    , on_canvas_resize# thì gọi hàm này
)     

# NHẤN CHUỘT TRÁI
image_canvas.bind(
    "<ButtonPress-1>",
    on_left_press
)
#Chuyển động
image_canvas.bind(
    "<B1-Motion>",
    on_left_drag
)
# THẢ CHUỘT
image_canvas.bind(
    "<ButtonRelease-1>",
    on_left_release
)
#CHUỘT PHẢI CHO HÀM PAN
image_canvas.bind(
    "<ButtonPress-3>",
    on_right_press
)

#Chuyển động
image_canvas.bind(
    "<B3-Motion>",
    on_right_drag
)
# THẢ CHUỘT
image_canvas.bind(
    "<ButtonRelease-3>",
    on_right_release
)
#-----ẢNH KẾT QUẢ----
result_canvas.bind(
    "<MouseWheel>",
    result_mouse_wheel_zoom
)
#CON LĂN CHO HÀM ZOOM (viewzoom)
#LĂN CHUỘT
image_canvas.bind(
    "<MouseWheel>",
    mouse_wheel_zoom
)
result_canvas.bind(
    "<ButtonPress-1>",
    start_result_pan
)


result_canvas.bind(
    "<B1-Motion>",
    drag_result_pan
)


result_canvas.bind(
    "<ButtonRelease-1>",
    end_result_pan
)

result_canvas.bind(
    "<Configure>",
    on_result_resize    
)
#-----CÁC HÀM XỬ LÝ XUẤT ẢNH-----
def save_result():
    if result_img is None:
        print("Chưa có ảnh kết quả để lưu!")

        status_label.configure(
            text="● Chưa có ảnh để lưu",
            text_color="#FCA5A5",
            fg_color="#450A0A"
        )

        return
    file_path = filedialog.asksaveasfilename(
        title="Lưu ảnh tài liệu",

        defaultextension=".jpg",

        filetypes=[
            ("JPEG Image", "*.jpg"),
            ("PNG Image", "*.png"),
            ("All files", "*.*")
        ]
    )
    # người dùng bấm Cancel
    if not file_path:
        return

    success = cv2.imwrite(
        file_path,
        result_img
    )
    if success:
        print(
            "Đã lưu ảnh:",
            file_path
        )
        status_label.configure(
            text="● Đã lưu kết quả",
            text_color="#22C55E",
            fg_color="#0F172A"
        )
    else:
        print(
            "Không thể lưu ảnh!"
        )
        status_label.configure(
            text="● Lưu ảnh thất bại",
            text_color="#FCA5A5",
            fg_color="#450A0A"
        )
#RESET TOÀN BỘ 
def reset_all():

    global input_img
    global original_img

    global current_corners
    global corner_select_mode
    global dragging_corner

    global scan_img
    global result_img

    global rotate_angle
    global resize_scale

    global zoom_scale
    global pan_x
    global pan_y

    global result_zoom_scale
    global result_pan_x
    global result_pan_y


    # ==============================
    # XÓA ẢNH
    # ==============================

    input_img = None

    original_img = None

    scan_img = None

    result_img = None


    # ==============================
    # XÓA CORNERS
    # ==============================

    current_corners = []

    corner_select_mode = False

    dragging_corner = None


    # ==============================
    # RESET SOURCE VIEW
    # ==============================

    zoom_scale = 1.0

    pan_x = 0

    pan_y = 0


    zoom_slider.set(100)

    zoom_value_label.configure(
        text="100%"
    )


    # ==============================
    # RESET RESULT VIEW
    # ==============================

    result_zoom_scale = 1.0

    result_pan_x = 0

    result_pan_y = 0


    # ==============================
    # RESET MẢNH 1
    # ==============================

    rotate_angle = 0

    resize_scale = 1.0
    resize_method_var.set(
        "AUTO"
    )

    rotate_slider.set(0)

    rotate_value_label.configure(
        text="0°"
    )
    resize_slider.set(100)
    resize_value_label.configure(
        text="100%"
    )
    method_label.configure(
        text="Using: Original"
    )
    # ==============================
    # XÓA SOURCE CANVAS
    # ==============================

    image_canvas.delete(
        "all"
    )
    image_canvas.create_text(

        image_canvas.winfo_width() / 2,

        image_canvas.winfo_height() / 2,

        text=(
            "Chưa có tài liệu\n"
            "Mở ảnh hoặc sử dụng Camera"
        ),

        fill=COLOR_TEXT_MUTED,

        font=(
            "Segoe UI",
            12
        )
    )
    # ==============================
    # XÓA RESULT CANVAS
    # ==============================

    result_canvas.delete(
        "all"
    )
    result_canvas.create_text(

        result_canvas.winfo_width() / 2,

        result_canvas.winfo_height() / 2,

        text="Chưa có kết quả",

        fill=COLOR_TEXT_MUTED,

        font=(
            "Segoe UI",
            12
        )
    )
    # ==============================
    # BUTTON STATE
    # ==============================
    scan_button.configure(
        state="disabled"
    )
    save_button.configure(
        state="disabled"
    )
    status_label.configure(
        text="● Sẵn sàng",
        text_color="#93C5FD",
        fg_color="#172554"
    )
    print(
        "Đã reset toàn bộ phiên làm việc"
    )
    
    #CLEAR KHI MỞ NHẦM TÀI LIỆU
def clear_old_document_state():
    global current_corners,scan_img,result_img
    current_corners = []
    scan_img = None
    result_img = None
    scan_button.configure(
        state="disabled"
    )
    save_button.configure(
        state="disabled"
    )
    result_canvas.delete(
        "all"
    )
#CHẠY APP
app.mainloop()
