import argparse
from sys import platform

from datetime import datetime

from models import *  # set ONNX_EXPORT in models.py
from utils.datasets import *
from utils.utils import *


def detect(save_img=False):
    img_size = (320, 192) if ONNX_EXPORT else opt.img_size  # (320, 192) or (416, 256) or (608, 352) for (height, width)
    out, source, weights, half, view_img, save_txt = opt.output, opt.source, opt.weights, opt.half, opt.view_img, opt.save_txt

    source = ["rtsp://luser:supersecretpassword@192.168.1.10:554/Streaming/Channels/101",
              "rtsp://luser:supersecretpassword@192.168.1.10:554/Streaming/Channels/201",
              "rtsp://luser:supersecretpassword@192.168.1.10:554/Streaming/Channels/301", 
              "rtsp://luser:supersecretpassword@192.168.1.10:554/Streaming/Channels/401"]

    spf = 5

    wantedClasses = [0, 14, 15, 16]
    
    # Initialize
    device = torch_utils.select_device(device='cpu' if ONNX_EXPORT else opt.device)

    # Initialize model
    model = Darknet(opt.cfg, img_size)

    # Load weights
    attempt_download(weights)
    if weights.endswith('.pt'):  # pytorch format
        model.load_state_dict(torch.load(weights, map_location=device)['model'])
    else:  # darknet format
        load_darknet_weights(model, weights)

    # Eval mode
    model.to(device).eval()

    # Export mode
    # if ONNX_EXPORT:
    #     img = torch.zeros((1, 3) + img_size)  # (1, 3, 320, 192)
    #     torch.onnx.export(model, img, 'weights/export.onnx', verbose=False, opset_version=10)

    #     # Validate exported model
    #     import onnx
    #     model = onnx.load('weights/export.onnx')  # Load the ONNX model
    #     onnx.checker.check_model(model)  # Check that the IR is well formed
    #     print(onnx.helper.printable_graph(model.graph))  # Print a human readable representation of the graph
    #     return

    # Half precision
    half = half and device.type != 'cpu'  # half precision only supported on CUDA
    if half:
        model.half()

    # Set Dataloader
    view_img = True
    save_img = True
    torch.backends.cudnn.benchmark = True  # set True to speed up constant image size inference
    dataset = LoadStreams(source, img_size=img_size, half=half)
    

    # Get names and colors
    names = load_classes(opt.names)
    colors = [[random.randint(0, 255) for _ in range(3)] for _ in range(len(names))]

    # Run inference
    for path, img, im0s, vid_cap in dataset:
        t = time.time()
        
        # Ge0 detections
        img = torch.from_numpy(img).to(device)
        if img.ndimension() == 3:
            img = img.unsqueeze(0)
        pred = model(img)[0]

        if opt.half:
            pred = pred.float()

        # Apply NMS
        pred = non_max_suppression(pred, opt.conf_thres, opt.iou_thres, classes=opt.classes, agnostic=opt.agnostic_nms)

        # Process detections
        for i, det in enumerate(pred):  # detections per image
            p, s, im0 = path[i], '%g: ' % i, im0s[i]

            save_path = str(Path(out) / Path(p).name)
            s += '%gx%g ' % img.shape[2:]  # print string
            if det is not None and len(det):
                # Rescale boxes from img_size to im0 size
                det[:, :4] = scale_coords(img.shape[2:], det[:, :4], im0.shape).round()

                # Print results
                for c in det[:, -1].unique():
                    n = (det[:, -1] == c).sum()  # detections per class
                    s += '%g %ss, ' % (n, names[int(c)])  # add to string

                # Write results
                notWanted = True
                for *xyxy, conf, cls in det:
                    if cls in wantedClasses:
                        notWanted = False

                    # if (xyxy[0]-xyxy[2])*(xyxy[1]-xyxy[3]) < 20000:
                    #     continue

                    if save_txt:  # Write to file
                        with open(save_path + '.txt', 'a') as file:
                            file.write(('%g ' * 6 + '\n') % (*xyxy, cls, conf))

                    if save_img or view_img:  # Add bbox to image
                        label = '%s %.2f' % (names[int(cls)], conf)
                        plot_one_box(xyxy, im0, label=label, color=colors[int(cls)])                
                
                # Print time (inference + NMS)
                print('%sDone. (%.3fs)' % (s, time.time() - t))
                if notWanted:
                    reason = 'unwanted class'
                    print('No detection made: {}'.format(reason))
                else:
                    detectedItems = "_".join(s.split(" ")[2:-1]).replace(",", "")
                    cv2.imwrite(save_path + '/{}-detected_{}.jpg'.format(datetime.now().strftime("%Y_%m_%d-%H_%M_%S"), detectedItems), im0)
            else:
                print('%sNothing Detected. (%.3fs)' % (s, time.time() - t))

        elapsed = time.time() - t
        if elapsed < spf:
            time.sleep(spf - elapsed)        

    if save_txt:
        print('Results saved to %s' % os.getcwd() + os.sep + out)
        if platform == 'darwin':  # MacOS
            os.system('open ' + out + ' ' + save_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cfg', type=str, default='cfg/yolov3-spp.cfg', help='*.cfg path')
    parser.add_argument('--names', type=str, default='data/coco.names', help='*.names path')
    parser.add_argument('--weights', type=str, default='weights/yolov3-spp.weights', help='path to weights file')
    parser.add_argument('--source', type=str, default='data/samples', help='source')  # input file/folder, 0 for webcam
    parser.add_argument('--output', type=str, default='output', help='output folder')  # output folder
    parser.add_argument('--img-size', type=int, default=416, help='inference size (pixels)')
    parser.add_argument('--conf-thres', type=float, default=0.5, help='object confidence threshold')
    parser.add_argument('--iou-thres', type=float, default=0.5, help='IOU threshold for NMS')
    parser.add_argument('--fourcc', type=str, default='mp4v', help='output video codec (verify ffmpeg support)')
    parser.add_argument('--half', action='store_true', help='half precision FP16 inference')
    parser.add_argument('--device', default='', help='device id (i.e. 0 or 0,1) or cpu')
    parser.add_argument('--view-img', action='store_true', help='display results')
    parser.add_argument('--save-txt', action='store_true', help='save results to *.txt')
    parser.add_argument('--classes', nargs='+', type=int, help='filter by class')
    parser.add_argument('--agnostic-nms', action='store_true', help='class-agnostic NMS')
    opt = parser.parse_args()
    print(opt)

    with torch.no_grad():
        detect()
