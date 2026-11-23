import sys
from PIL import Image, ImageDraw, ImageFilter, ImageChops
sys.path.insert(0, '/home/claude/d003')
import holo3 as V
import holo4 as H4
import holo7 as H7
W, H = 1080, 1920
im = Image.open('/home/claude/d003/b3d/final_front.png').convert('RGB')
small = im.resize((im.width // 6, im.height // 6), Image.BILINEAR)
bright = small.point(lambda v: max(0, v - 150) * 2.2).filter(ImageFilter.GaussianBlur(6)).resize(im.size, Image.BILINEAR)
im = ImageChops.screen(im, bright).resize((W, H), Image.LANCZOS)
im = ImageChops.multiply(im, H4.make_vign())
g = Image.linear_gradient('L').resize((W, 700)).transpose(Image.FLIP_TOP_BOTTOM).point(lambda v: int(v * 0.75))
dark = Image.new('RGB', (W, 700), (0, 8, 12)); im.paste(dark, (0, 0), g)
d = ImageDraw.Draw(im, 'RGBA')
V.text(im, d, (W / 2, 320), "TON POÊLE", V.font("Black", 118), (255, 255, 255), 1.0, 'mm', 8)
V.text(im, d, (W / 2, 470), "S'ALLUME TOUT SEUL", V.font("Black", 84), V.FOCUS, 1.0, 'mm', 10)
V.text(im, d, (W / 2, 1520), "Le fonctionnement complet en 3D", V.font('Bold', 52), (110, 245, 255), 1.0, 'mm', 6)
lg = H7.logo_disc(120); im.paste(lg, (W - 60 - 120, 120), lg)
im.save('/home/claude/d003/couverture.jpg', quality=93)
print('ok')
