import sys
from PIL import Image, ImageDraw, ImageFilter, ImageChops
sys.path.insert(0, '/home/claude/v7')
import holo3 as V
import holo4 as H4
import holo7 as H7
W, H = 1080, 1920
im = Image.open('/home/claude/b3d/final_hook1.png').convert('RGB')
small = im.resize((im.width // 6, im.height // 6), Image.BILINEAR)
bright = small.point(lambda v: max(0, v - 150) * 2.2).filter(ImageFilter.GaussianBlur(6)).resize(im.size, Image.BILINEAR)
im = ImageChops.screen(im, bright).resize((W, H), Image.LANCZOS)
im = ImageChops.multiply(im, H4.make_vign())
d = ImageDraw.Draw(im, 'RGBA')
V.text(im, d, (W / 2, 330), "TA CHAUDIÈRE", V.font('Black', 104), (255, 255, 255), 1.0, 'mm', 8)
V.text(im, d, (W / 2, 470), "PLEURE ?", V.font('Black', 168), V.FOCUS, 1.0, 'mm', 10)
V.text(im, d, (W / 2, 1520), "Le fonctionnement complet en 3D", V.font('Bold', 52), (110, 245, 255), 1.0, 'mm', 6)
lg = H7.logo_disc(120); im.paste(lg, (W - 60 - 120, 120), lg)
im.save('/home/claude/v7/couverture_neuronade.jpg', quality=93)
print('ok')
