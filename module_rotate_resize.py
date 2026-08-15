import cv2
import matplotlib.pyplot as plt
import numpy as np

def zoom_pic(img,wid=None,scale=None,model=cv2.INTER_LINEAR):
  h,w,_=img.shape
  if scale is not None:
    wid = int(w * scale)
  if wid is None:
    return img
  h_new=int(h*(wid/w))
  img_new=cv2.resize(img,(wid,h_new),interpolation=model)
  return img_new

def rotation_pic(img,angle:float):
  h,w,_=img.shape
  center=(w/2,h/2)
  T=cv2.getRotationMatrix2D(center,angle,1.0)
  cos= np.abs(T[0,0])
  sin= np.abs(T[0,1])
  nW=int((w*cos)+(h*sin))
  nH=int((w*sin)+(h*cos))
  T[0,2]+=nW/2-center[0]
  T[1,2]+=nH/2-center[1]
  img_new=cv2.warpAffine(img,T,(nW,nH))
  return img_new