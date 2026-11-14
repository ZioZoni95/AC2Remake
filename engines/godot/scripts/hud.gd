extends Control
## HUD in stile Ace Combat, disegnato in 2D. I dati arrivano da flight_demo.gd / live_view.gd in `d`:
## speed (km/h), alt (m), thr (0..1), ammo, enemies, pitch/roll (rad), heading (gradi), blips [[x_destra, z_avanti], ...] in metri,
## radar_range (m), target {screen: Vector2, dist: m} oppure {}, cockpit (bool).
var d: Dictionary = {}
const G := Color(0.35, 1.0, 0.45)
const GD := Color(0.35, 1.0, 0.45, 0.35)
const RED := Color(1.0, 0.3, 0.3)

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_preset(Control.PRESET_FULL_RECT)

func _t(p: Vector2, s: String, size := 18, col := G, align := HORIZONTAL_ALIGNMENT_LEFT) -> void:
	draw_string(ThemeDB.fallback_font, p, s, align, -1, size, col)

func _draw() -> void:
	if d.is_empty():
		return
	var sz := get_viewport_rect().size
	var c := sz / 2.0
	_ladder(c, sz)
	_compass(sz)
	_tapes(sz)
	_radar(sz)
	_target()
	# mirino
	draw_arc(c, 14.0, 0.0, TAU, 24, G, 1.5)
	draw_line(c + Vector2(-26, 0), c + Vector2(-14, 0), G, 1.5); draw_line(c + Vector2(14, 0), c + Vector2(26, 0), G, 1.5)
	draw_line(c + Vector2(0, -26), c + Vector2(0, -14), G, 1.5)
	_t(Vector2(sz.x - 14, sz.y - 14), "C: camera %s   +/-: distanza" % ("cabina" if d.get("cockpit", false) else "esterna"), 14, GD, HORIZONTAL_ALIGNMENT_RIGHT)

func _ladder(c: Vector2, sz: Vector2) -> void:
	var pitch: float = d["pitch"]; var roll: float = d["roll"]
	var ppd := sz.y / 70.0                                  # pixel per grado
	var rot := Transform2D(-roll, c)
	for deg in range(-40, 41, 10):
		var y := (deg - rad_to_deg(pitch)) * ppd * -1.0 * -1.0
		y = (rad_to_deg(pitch) - deg) * ppd
		if absf(y) > sz.y * 0.4:
			continue
		var w := 90.0 if deg != 0 else 160.0
		var a := rot * Vector2(-w, y); var b := rot * Vector2(-w * 0.3, y)
		var a2 := rot * Vector2(w * 0.3, y); var b2 := rot * Vector2(w, y)
		var col := G if deg >= 0 else GD
		draw_line(a, b, col, 1.5); draw_line(a2, b2, col, 1.5)
		if deg != 0:
			_t(rot * Vector2(-w - 36, y + 6), str(abs(deg)), 14, col)
			_t(rot * Vector2(w + 8, y + 6), str(abs(deg)), 14, col)

func _compass(sz: Vector2) -> void:
	var hdg: float = d["heading"]
	var x0 := sz.x / 2.0
	draw_line(Vector2(x0 - 160, 40), Vector2(x0 + 160, 40), GD, 1.0)
	for k in range(-8, 9):
		var deg := (int(hdg / 10.0) + k) * 10
		var x := x0 + (deg - hdg) * 4.0
		if absf(x - x0) > 160: continue
		draw_line(Vector2(x, 40), Vector2(x, 48 if deg % 30 == 0 else 44), G, 1.5)
		if deg % 30 == 0:
			_t(Vector2(x, 66), "%03d" % (((deg % 360) + 360) % 360), 14, G, HORIZONTAL_ALIGNMENT_CENTER)
	draw_colored_polygon(PackedVector2Array([Vector2(x0, 34), Vector2(x0 - 6, 24), Vector2(x0 + 6, 24)]), G)
	_t(Vector2(x0, 20), "%03d" % (((int(hdg) % 360) + 360) % 360), 16, G, HORIZONTAL_ALIGNMENT_CENTER)

func _tapes(sz: Vector2) -> void:
	var yc := sz.y / 2.0
	var spd: float = d["speed"]; var alt: float = d["alt"]
	# velocita' a sinistra
	draw_rect(Rect2(Vector2(60, yc - 16), Vector2(110, 32)), GD, false, 1.5)
	_t(Vector2(66, yc + 7), "VEL %d" % int(spd), 20)
	# quota a destra
	draw_rect(Rect2(Vector2(sz.x - 190, yc - 16), Vector2(130, 32)), GD, false, 1.5)
	_t(Vector2(sz.x - 184, yc + 7), "ALT %d" % int(alt), 20)
	# motore: barra verticale a sinistra
	var thr: float = d["thr"]
	var bx := 40.0; var by := yc - 90.0
	draw_rect(Rect2(Vector2(bx, by), Vector2(10, 180)), GD, false, 1.5)
	draw_rect(Rect2(Vector2(bx, by + 180.0 * (1.0 - thr)), Vector2(10, 180.0 * thr)), G)
	_t(Vector2(bx - 8, by + 198), "MOT", 14)
	# in basso al centro: missili, nemici, danno
	var base := Vector2(sz.x / 2.0, sz.y - 40)
	_t(base + Vector2(-210, 0), "MISSILI %d" % int(d["ammo"]), 20)
	_t(base + Vector2(-20, 0), "NEMICI %d" % int(d["enemies"]), 20, RED if d["enemies"] > 0 else G)
	_t(base + Vector2(130, 0), "DANNO %d%%" % int(d.get("damage", 0)), 20)

func _radar(sz: Vector2) -> void:
	var r := 86.0
	var c := Vector2(120.0, sz.y - 130.0)
	draw_circle(c, r, Color(0.0, 0.12, 0.04, 0.55))
	draw_arc(c, r, 0.0, TAU, 48, G, 1.5); draw_arc(c, r * 0.5, 0.0, TAU, 32, GD, 1.0)
	draw_line(c + Vector2(-r, 0), c + Vector2(r, 0), GD, 1.0); draw_line(c + Vector2(0, -r), c + Vector2(0, r), GD, 1.0)
	var rng: float = d.get("radar_range", 4000.0)
	for b in d["blips"]:
		var p := Vector2(b[0], -b[1]) / rng * r
		if p.length() > r - 3.0:
			p = p.normalized() * (r - 3.0)
		draw_rect(Rect2(c + p - Vector2(3, 3), Vector2(6, 6)), RED)
	draw_colored_polygon(PackedVector2Array([c + Vector2(0, -7), c + Vector2(-5, 6), c + Vector2(5, 6)]), G)
	_t(c + Vector2(-r, r + 18), "RADAR %d km" % int(rng / 1000.0), 14, GD)

func _target() -> void:
	var tg: Dictionary = d.get("target", {})
	if tg.is_empty():
		return
	var p: Vector2 = tg["screen"]; var s := 30.0
	for sx in [-1, 1]:
		for sy in [-1, 1]:
			var corner := p + Vector2(sx * s, sy * s)
			draw_line(corner, corner + Vector2(-sx * 12, 0), RED, 2.0); draw_line(corner, corner + Vector2(0, -sy * 12), RED, 2.0)
	_t(p + Vector2(s + 8, 6), "%d m" % int(tg["dist"]), 16, RED)
