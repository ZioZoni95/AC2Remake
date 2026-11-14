extends Node3D
## DEMO di Fighter's Honor: volo arcade con l'XFA-27 sul terreno originale, le unita' della lista T1, missili e HUD.
## SEMPLIFICAZIONI (da migliorare): i nemici non sparano, comportamento minimo (aerei in cerchio, terrestri fermi), scala e
## velocita' scelte a mano, nessuna manovra T7/T8, obiettivo = distruggere tutti i nemici (squadra != 0).
## Comandi: freccia su/giu = beccheggio, sinistra/destra = rollio+virata, A/D = imbardata, W/S = motore, Spazio = missile,
## R = ricomincia, H = aiuto, Esc = esci. Dati: res://assets/fighters_honor/ (mission.json, terreno.*, unita_*.gltf).

const DIR := "res://assets/fighters_honor/"
const WS := 0.02                 # metri per unita' di mondo (ipotesi)
const MODEL_SCALE := WS / 0.01   # i glTF sono a 0.01 m per unita'

var _terr_h := PackedFloat32Array()
var _n := 0
var _step := 1024.0
var _x0 := 0.0
var _z0 := 0.0
var _sea := 34.0

var _player := Node3D.new()
var _cam := Camera3D.new()
var _speed := 150.0
var _throttle := 1.0
var _units: Array = []           # {node, alive, enemy, air, t, c, orbit}
var _missiles: Array = []
var _fx: Array = []
var _cache := {}
var _hud := Label.new()
var _msg := Label.new()
var _ammo := 12
var _won := false
var _start := Vector3.ZERO
var _fire_cd := 0.0
var _test := false
var _frame := 0

func _ready() -> void:
	_test = OS.get_cmdline_user_args().has("--autotest")
	var env := WorldEnvironment.new(); env.environment = Environment.new()
	var sky := Sky.new(); var pm := ProceduralSkyMaterial.new()
	pm.sky_top_color = Color(0.18, 0.38, 0.75); pm.sky_horizon_color = Color(0.72, 0.80, 0.90)
	pm.ground_horizon_color = Color(0.55, 0.62, 0.66); pm.ground_bottom_color = Color(0.20, 0.30, 0.38)
	sky.sky_material = pm
	env.environment.background_mode = Environment.BG_SKY; env.environment.sky = sky
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.environment.fog_enabled = true; env.environment.fog_density = 0.00015
	env.environment.fog_light_color = Color(0.72, 0.80, 0.90)
	add_child(env)
	var sun := DirectionalLight3D.new(); sun.rotation_degrees = Vector3(-45, 35, 0); sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 600.0
	add_child(sun)
	_load_terrain()
	var d: Dictionary = JSON.parse_string(FileAccess.open(DIR + "mission.json", FileAccess.READ).get_as_text())
	var pp: Array = d["giocatore"]["pos"]
	_start = _w2g(pp)
	var pm3 := _load_model("res://assets/aerei/xfa27_smooth1_hd.gltf")
	if pm3 != null:
		pm3.scale = Vector3.ONE * MODEL_SCALE
		pm3.rotation.y = PI   # il naso dei modelli estratti punta a +Z, il volo usa -Z come avanti
		_player.add_child(pm3)
	add_child(_player)
	add_child(_cam); _cam.current = true; _cam.fov = 65.0; _cam.far = 12000.0
	for u in d["unita"]:
		_spawn_unit(u)
	var layer := CanvasLayer.new(); add_child(layer)
	_hud.position = Vector2(14, 10); _hud.add_theme_font_size_override("font_size", 18); layer.add_child(_hud)
	_msg.position = Vector2(330, 220); _msg.add_theme_font_size_override("font_size", 36); layer.add_child(_msg)
	var ch := Label.new(); ch.text = "+"; ch.position = Vector2(474, 252); ch.add_theme_font_size_override("font_size", 28); layer.add_child(ch)
	_reset()

func _w2g(p: Array) -> Vector3:
	return Vector3(p[0] * WS, -p[1] * WS, p[2] * WS)

func _load_terrain() -> void:
	var meta: Dictionary = JSON.parse_string(FileAccess.open(DIR + "terreno.json", FileAccess.READ).get_as_text())
	_n = int(meta["lato"]); _step = float(meta["passo"]); _x0 = float(meta["x0"]); _z0 = float(meta["z0"])
	var f := FileAccess.open(DIR + "terreno.i16", FileAccess.READ)
	var raw := f.get_buffer(_n * _n * 2)
	_terr_h.resize(_n * _n)
	for i in range(_n * _n):
		_terr_h[i] = float(raw.decode_s16(i * 2))
	var verts := PackedVector3Array(); var cols := PackedColorArray(); var idx := PackedInt32Array()
	verts.resize(_n * _n); cols.resize(_n * _n)
	for j in range(_n):
		for i in range(_n):
			var h := _terr_h[j * _n + i]
			verts[j * _n + i] = Vector3((_x0 + i * _step) * WS, h * WS, (_z0 + j * _step) * WS)
			cols[j * _n + i] = _color_for(h)
	for j in range(_n - 1):
		for i in range(_n - 1):
			var a := j * _n + i; var b := a + 1; var c := a + _n; var e := c + 1
			idx.append_array([a, b, c, b, e, c])
	var st := SurfaceTool.new(); st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for k in range(verts.size()):
		st.set_color(cols[k]); st.add_vertex(verts[k])
	for k in idx: st.add_index(k)
	st.generate_normals()
	var mi := MeshInstance3D.new(); mi.mesh = st.commit()
	var m := StandardMaterial3D.new(); m.vertex_color_use_as_albedo = true; m.roughness = 0.9
	mi.material_override = m; mi.visible = false; add_child(mi)   # solo collisione: il terreno disegnato e' la mesh originale HD
	var real := _load_model(DIR + "terreno_mesh_hd.gltf")
	if real != null:
		add_child(real)
	else:
		mi.visible = true
	# nessun mare: nel gioco le tessere senza dati (magic 0x5907) sono pianura a quota fissa (FUN_8002703c)
	var plain := MeshInstance3D.new(); var pl := PlaneMesh.new(); pl.size = Vector2(60000, 60000); plain.mesh = pl
	var pmat := StandardMaterial3D.new(); pmat.albedo_color = Color(0.30, 0.42, 0.22); pmat.roughness = 1.0
	plain.material_override = pmat; plain.position = Vector3(0, _sea * WS, 0); add_child(plain)

func _color_for(h: float) -> Color:
	if h <= _sea + 8.0: return Color(0.30, 0.42, 0.22)       # pianura
	if h < 700.0: return Color(0.28, 0.45, 0.22)
	if h < 1800.0: return Color(0.42, 0.38, 0.30)
	return Color(0.88, 0.90, 0.92)

## altezza del suolo (m) con interpolazione bilineare; fuori mappa = mare
func ground_m(p: Vector3) -> float:
	var fx := (p.x / WS - _x0) / _step; var fz := (p.z / WS - _z0) / _step
	if fx < 0 or fz < 0 or fx >= _n - 1 or fz >= _n - 1:
		return _sea * WS
	var i := int(fx); var j := int(fz); var tx := fx - i; var tz := fz - j
	var h00 := _terr_h[j * _n + i]; var h10 := _terr_h[j * _n + i + 1]
	var h01 := _terr_h[(j + 1) * _n + i]; var h11 := _terr_h[(j + 1) * _n + i + 1]
	return maxf(lerpf(lerpf(h00, h10, tx), lerpf(h01, h11, tx), tz), _sea) * WS

func _spawn_unit(u: Dictionary) -> void:
	var t := int(u["tipo"]); var node := _make_unit(t)
	var p := _w2g(u["pos"])
	var air := int(u["categoria"]) in [1, 4, 7]
	if bool(u["a_terra"]) or not air:
		p.y = ground_m(p) + 0.5
	node.position = p; node.scale = Vector3.ONE * MODEL_SCALE
	var enemy := int(u["squadra"]) != 0
	add_child(node)
	var mk := Label3D.new(); mk.text = "▼"; mk.billboard = BaseMaterial3D.BILLBOARD_ENABLED; mk.fixed_size = true; mk.pixel_size = 0.0009
	mk.no_depth_test = true; mk.modulate = Color(1, 0.2, 0.2) if enemy else Color(0.3, 1, 0.4); mk.position = Vector3(0, 6, 0)
	node.add_child(mk)
	_units.append({"node": node, "alive": true, "enemy": enemy, "air": air, "c": p, "ph": randf() * TAU, "slot": u["slot"], "mk": mk})

func _make_unit(t: int) -> Node3D:
	var base := "unita_%02d" % (3 * clampi(t, 0, 12) + 2)
	var path := DIR + base + ".gltf"
	if FileAccess.file_exists(DIR + base + "_smooth1_hd.gltf"):
		path = DIR + base + "_smooth1_hd.gltf"
	if not _cache.has(path):
		_cache[path] = _load_model(path)
	var tm: Node = _cache[path]
	if tm == null:
		var s := MeshInstance3D.new(); s.mesh = BoxMesh.new(); return s
	return tm.duplicate() as Node3D

func _load_model(path: String) -> Node3D:
	var doc := GLTFDocument.new(); var st := GLTFState.new()
	if doc.append_from_file(ProjectSettings.globalize_path(path), st) != OK:
		push_error("glTF non caricato: " + path); return null
	var root := doc.generate_scene(st) as Node3D
	for mi in root.find_children("*", "MeshInstance3D", true, false):
		var m := mi as MeshInstance3D
		for s in range(m.mesh.get_surface_count()):
			var sm := m.mesh.surface_get_material(s)
			if sm is StandardMaterial3D:
				var dm := (sm as StandardMaterial3D).duplicate() as StandardMaterial3D
				dm.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
				dm.vertex_color_use_as_albedo = false; dm.metallic = 0.3; dm.roughness = 0.5
				m.set_surface_override_material(s, dm)
	return root

func _reset() -> void:
	_player.position = _start; _player.basis = Basis(Vector3.UP, PI)   # naso verso +z
	_speed = 150.0; _throttle = 1.0; _ammo = 12; _won = false; _msg.text = ""
	for u in _units:
		u["alive"] = true; (u["node"] as Node3D).visible = true

func _process(dt: float) -> void:
	_frame += 1
	_fire_cd = maxf(_fire_cd - dt, 0.0)
	_fly(dt); _update_units(dt); _update_missiles(dt); _update_fx(dt); _update_cam(dt); _update_hud()
	if _test and _frame == 90:
		print("AUTOTEST pos=", _player.position, " speed=", _speed, " nemici=", _enemies_left()); get_tree().quit()

func _fly(dt: float) -> void:
	var b := _player.basis
	var pitch := 0.0; var roll := 0.0; var yaw := 0.0
	if Input.is_key_pressed(KEY_UP): pitch -= 1.0
	if Input.is_key_pressed(KEY_DOWN): pitch += 1.0
	if Input.is_key_pressed(KEY_LEFT): roll += 1.0
	if Input.is_key_pressed(KEY_RIGHT): roll -= 1.0
	if Input.is_key_pressed(KEY_A): yaw += 1.0
	if Input.is_key_pressed(KEY_D): yaw -= 1.0
	if Input.is_key_pressed(KEY_W): _throttle = minf(_throttle + dt * 0.6, 1.4)
	if Input.is_key_pressed(KEY_S): _throttle = maxf(_throttle - dt * 0.6, 0.4)
	b = b.rotated(b.x, pitch * 1.1 * dt)
	b = b.rotated(b.z, -roll * 1.6 * dt)
	b = b.rotated(Vector3.UP, (yaw * 0.7 + roll * 0.55 * clampf(b.y.dot(Vector3.RIGHT) * 0.0 + 1.0, 0, 1)) * dt)
	# autostabilizzazione lieve del rollio quando non si preme nulla
	if roll == 0.0:
		var side := b.x.y
		b = b.rotated(b.z, side * 1.2 * dt)
	_player.basis = b.orthonormalized()
	_speed = lerpf(_speed, 150.0 * _throttle, dt * 0.8)
	_player.position += -_player.basis.z * _speed * dt
	var g := ground_m(_player.position)
	if _player.position.y < g + 3.0:
		_msg.text = "SCHIANTO  -  R per ricominciare"
		_player.position.y = g + 3.0
		_speed = 0.0

func _update_units(dt: float) -> void:
	for u in _units:
		if not u["alive"] or not u["air"]:
			continue
		u["ph"] = float(u["ph"]) + dt * 0.12
		var c: Vector3 = u["c"]; var r := 320.0
		var n: Node3D = u["node"]
		var np := c + Vector3(cos(u["ph"]) * r, 0, sin(u["ph"]) * r)
		var dirv := np - n.position
		if dirv.length() > 0.01:
			n.basis = Basis.looking_at(-dirv.normalized(), Vector3.UP).scaled(Vector3.ONE * MODEL_SCALE)
		n.position = np

func _enemies_left() -> int:
	var k := 0
	for u in _units:
		if u["alive"] and u["enemy"]: k += 1
	return k

func _target() -> Dictionary:
	var best: Dictionary = {}; var bd := 4000.0
	var fwd := -_player.basis.z
	for u in _units:
		if not u["alive"] or not u["enemy"]: continue
		var v: Vector3 = (u["node"] as Node3D).position - _player.position
		var dist := v.length()
		if dist < bd and v.normalized().dot(fwd) > 0.82:
			bd = dist; best = u
	return best

func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventKey and e.pressed and not e.echo:
		if e.keycode == KEY_SPACE and _ammo > 0 and _fire_cd <= 0.0 and not _won:
			_ammo -= 1; _fire_cd = 0.35
			_missiles.append({"p": _player.position + -_player.basis.z * 6.0, "v": -_player.basis.z * (_speed + 350.0),
				"t": _target(), "life": 7.0, "node": _make_missile()})
		if e.keycode == KEY_R: _reset()
		if e.keycode == KEY_ESCAPE: get_tree().quit()

func _make_missile() -> Node3D:
	var m := MeshInstance3D.new(); var cm := CylinderMesh.new(); cm.top_radius = 0.12; cm.bottom_radius = 0.12; cm.height = 2.2; m.mesh = cm
	var mat := StandardMaterial3D.new(); mat.albedo_color = Color(0.9, 0.9, 0.95); mat.emission_enabled = true; mat.emission = Color(1, 0.6, 0.2); mat.emission_energy_multiplier = 1.5
	m.material_override = mat; add_child(m); return m

func _update_missiles(dt: float) -> void:
	for mi in range(_missiles.size() - 1, -1, -1):
		var ms: Dictionary = _missiles[mi]
		ms["life"] = float(ms["life"]) - dt
		var tg: Dictionary = ms["t"]
		if not tg.is_empty() and tg["alive"]:
			var want: Vector3 = ((tg["node"] as Node3D).position - ms["p"]).normalized() * 520.0
			ms["v"] = (ms["v"] as Vector3).lerp(want, clampf(dt * 2.5, 0, 1))
		ms["p"] = (ms["p"] as Vector3) + (ms["v"] as Vector3) * dt
		var node: Node3D = ms["node"]; node.position = ms["p"]
		if (ms["v"] as Vector3).length() > 1.0:
			node.basis = Basis.looking_at((ms["v"] as Vector3).normalized(), Vector3.UP) * Basis(Vector3.RIGHT, PI / 2)
		var hit := false
		for u in _units:
			if u["alive"] and u["enemy"] and ((u["node"] as Node3D).position - (ms["p"] as Vector3)).length() < 28.0:
				_kill(u); hit = true; break
		if hit or ms["life"] <= 0.0 or (ms["p"] as Vector3).y < ground_m(ms["p"]):
			if not hit and ms["life"] > 0.0: _boom(ms["p"], 0.5)
			node.queue_free(); _missiles.remove_at(mi)

func _kill(u: Dictionary) -> void:
	u["alive"] = false; (u["node"] as Node3D).visible = false
	_boom((u["node"] as Node3D).position, 1.0)
	if _enemies_left() == 0:
		_won = true; _msg.text = "MISSIONE COMPIUTA"

func _boom(p: Vector3, s: float) -> void:
	var m := MeshInstance3D.new(); var sp := SphereMesh.new(); sp.radius = 4.0 * s; sp.height = 8.0 * s; m.mesh = sp
	var mat := StandardMaterial3D.new(); mat.albedo_color = Color(1, 0.55, 0.15); mat.emission_enabled = true; mat.emission = Color(1, 0.5, 0.1)
	mat.emission_energy_multiplier = 3.0; mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.material_override = mat; m.position = p; add_child(m); _fx.append({"n": m, "t": 0.0})

func _update_fx(dt: float) -> void:
	for i in range(_fx.size() - 1, -1, -1):
		var f: Dictionary = _fx[i]; f["t"] = float(f["t"]) + dt
		var k := float(f["t"]); (f["n"] as Node3D).scale = Vector3.ONE * (1.0 + k * 5.0)
		if k > 0.7:
			(f["n"] as Node3D).queue_free(); _fx.remove_at(i)

func _update_cam(dt: float) -> void:
	var k := clampf(_speed / 210.0, 0.0, 1.0)                        # distanza e campo visivo crescono con la velocita'
	_cam.fov = lerpf(62.0, 74.0, k)
	var want := _player.position + _player.basis * Vector3(0, lerpf(1.6, 2.4, k), lerpf(4.5, 8.0, k))
	_cam.position = _cam.position.lerp(want, clampf(dt * 6.0, 0, 1))
	_cam.look_at(_player.position + _player.basis * Vector3(0, 0.8, -10.0), _player.basis.y)

func _update_hud() -> void:
	var alt := _player.position.y - ground_m(_player.position)
	var t := _target()
	_hud.text = "VEL %d km/h   QUOTA %d m   MOTORE %d%%   MISSILI %d   NEMICI %d%s\nSu/Giu beccheggio  Sx/Dx virata  A/D imbardata  W/S motore  Spazio missile  R ricomincia" % [
		int(_speed * 3.6), int(alt), int(_throttle * 100.0 / 1.4 * 1.0), _ammo, _enemies_left(), ("   [BERSAGLIO IN MIRA]" if not t.is_empty() else "")]
