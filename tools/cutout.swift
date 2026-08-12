import Foundation
import Vision
import CoreImage

let a = CommandLine.arguments
guard a.count >= 3, let img = CIImage(contentsOf: URL(fileURLWithPath: a[1])) else {
    FileHandle.standardError.write("usage: cutout <in.png> <out.png>\n".data(using: .utf8)!); exit(1)
}
let handler = VNImageRequestHandler(ciImage: img, options: [:])
let req = VNGenerateForegroundInstanceMaskRequest()
do { try handler.perform([req]) } catch { print("perform失敗: \(error)"); exit(1) }
guard let obs = req.results?.first else { print("被写体を検出できず"); exit(1) }
print("検出インスタンス数: \(obs.allInstances.count)")
let maskBuf = try obs.generateScaledMaskForImage(forInstances: obs.allInstances, from: handler)
let mask = CIImage(cvPixelBuffer: maskBuf)

let f = CIFilter(name: "CIBlendWithMask")!
f.setValue(img, forKey: kCIInputImageKey)
f.setValue(CIImage(color: .clear).cropped(to: img.extent), forKey: kCIInputBackgroundImageKey)
f.setValue(mask, forKey: kCIInputMaskImageKey)
guard let out = f.outputImage else { print("合成失敗"); exit(1) }

let ctx = CIContext()
try ctx.writePNGRepresentation(of: out, to: URL(fileURLWithPath: a[2]),
                               format: .RGBA8, colorSpace: CGColorSpaceCreateDeviceRGB())
print("書き出し: \(a[2])")
