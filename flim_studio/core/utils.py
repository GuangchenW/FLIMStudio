import hashlib
import colorsys

def str2color(text:str) -> str:
	"""
	Return a hex color hashed from input text.
	"""
	# Hash to hue
	h = int(hashlib.sha1(text.encode("utf-8")).hexdigest()[:8], 16)
	# Map to hue in [0,1)
	hue = (h%360)/360.0
	saturation = 0.65
	value = 0.95

	r,g,b = colorsys.hsv_to_rgb(hue, saturation, value)
	hex_str = "#{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(b*255))
	return hex_str