extends Node3D
## DEMO di Fighter's Honor: volo arcade con l'XFA-27 sul terreno originale, le unita' della lista T1, missili e HUD.
## SEMPLIFICAZIONI (da migliorare): i nemici non sparano, comportamento minimo (aerei in cerchio, terrestri fermi), scala e
## velocita' scelte a mano, nessuna manovra T7/T8, obiettivo = distruggere tutti i nemici (squadra != 0).
## Comandi: freccia su/giu = beccheggio, sinistra/destra = rollio+virata, A/D = imbardata, W/S = motore, Spazio = missile,
## +/- = distanza della camera, R = ricomincia, Esc = esci. Dati: res://assets/fighters_honor/ (mission.json, terreno.*, unita_*.gltf).

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
const AUDIO := "res://assets/audio/"
var _music := AudioStreamPlayer.new()      # musica: tracce originali XA decodificate (SCOPERTE #33), N = traccia successiva
var _eng := AudioStreamPlayer.new()        # motore: SEGNAPOSTO sintetico
var _sfx_pl: Dictionary = {}
var _tracks: Array = []
var _ti := 0
var _lock_cd := 0.0
var _cockpit := false
var _envr: Environment
var _sun := DirectionalLight3D.new()
var _q := 1                  # qualita': 0 bassa, 1 media (predefinita), 2 alta - tasto G
var _hud2: Control
var _cz := 1.0              # zoom della camera di inseguimento: tasti + e -
var _test := false
var _fxtest := false
var _frame := 0

func _ready() -> void:
	_test = OS.get_cmdline_user_args().has("--autotest")
	_cockpit = OS.get_cmdline_user_args().has("--cockpit")
	_fxtest = OS.get_cmdline_user_args().has("--fx")   # prova degli effetti: un'esplosione davanti all'aereo al fotogramma 12
	var env := WorldEnvironment.new(); env.environment = Environment.new()
	var sky := Sky.new(); var pm := ProceduralSkyMaterial.new()
	pm.sky_top_color = Color(0.06, 0.22, 0.60); pm.sky_horizon_color = Color(0.50, 0.66, 0.86)
	pm.ground_horizon_color = Color(0.55, 0.62, 0.66); pm.ground_bottom_color = Color(0.20, 0.30, 0.38)
	sky.sky_material = pm
	env.environment.background_mode = Environment.BG_SKY; env.environment.sky = sky
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.environment.ambient_light_energy = 0.55
	env.environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.environment.fog_enabled = true; env.environment.fog_density = 0.00015
	env.environment.fog_light_color = Color(0.50, 0.64, 0.84)
	env.environment.adjustment_enabled = true   # grading: piu' contrasto e colore (lo schermo era troppo bianco)
	env.environment.adjustment_contrast = 1.14; env.environment.adjustment_saturation = 1.22; env.environment.adjustment_brightness = 0.95
	_envr = env.environment
	add_child(env)
	_sun.rotation_degrees = Vector3(-45, 35, 0); _sun.light_energy = 1.25; _sun.shadow_enabled = true
	_sun.directional_shadow_max_distance = 350.0; _sun.directional_shadow_mode = DirectionalLight3D.SHADOW_ORTHOGONAL
	add_child(_sun)
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
	_hud2 = (load("res://scripts/hud.gd") as GDScript).new(); layer.add_child(_hud2)
	_setup_audio()
	_apply_quality()
	_reset()

## Profili di qualita' (tasto G): 0 bassa = niente SSAO/glow/ombre/MSAA; 1 media = glow + ombre vicine + FXAA; 2 alta = anche SSAO e MSAA 2x
func _apply_quality() -> void:
	var vp := get_viewport()
	_envr.ssao_enabled = (_q >= 2)
	_envr.glow_enabled = (_q >= 1)
	_sun.shadow_enabled = (_q >= 1)
	vp.msaa_3d = Viewport.MSAA_2X if _q >= 2 else Viewport.MSAA_DISABLED
	vp.screen_space_aa = Viewport.SCREEN_SPACE_AA_FXAA if _q == 1 else Viewport.SCREEN_SPACE_AA_DISABLED

## WAV a 44 byte (come li scrive il modulo wave di Python): canali a +22, frequenza a +24, PCM 16 bit
func _wav(path: String, loop: bool) -> AudioStreamWAV:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		return null
	var b := f.get_buffer(f.get_length())
	var st := AudioStreamWAV.new()
	st.format = AudioStreamWAV.FORMAT_16_BITS
	st.stereo = b.decode_u16(22) == 2
	st.mix_rate = b.decode_u32(24)
	st.data = b.slice(44)
	if loop:
		st.loop_mode = AudioStreamWAV.LOOP_FORWARD
		st.loop_begin = 0
		st.loop_end = st.data.size() / (4 if st.stereo else 2)
	return st

func _setup_audio() -> void:
	add_child(_music); add_child(_eng)
	_music.volume_db = -7.0
	_eng.stream = _wav(AUDIO + "sfx_motore.wav", true); _eng.volume_db = -10.0
	if _eng.stream != null:
		_eng.play()
	for n in ["lancio", "esplosione", "aggancio"]:
		var p := AudioStreamPlayer.new(); p.stream = _wav(AUDIO + "sfx_%s.wav" % n, false); add_child(p); _sfx_pl[n] = p
	for fn in DirAccess.get_files_at(AUDIO):
		if fn.begins_with("traccia_") and fn.ends_with(".wav"):
			_tracks.append(fn)
	_tracks.sort()
	if _tracks.size() > 0:
		_play_track(0)

func _play_track(i: int) -> void:
	_ti = posmod(i, _tracks.size())
	var s := _wav(AUDIO + _tracks[_ti], true)
	if s != null:
		_music.stream = s; _music.play()

func _sfx(n: String) -> void:
	if _sfx_pl.has(n) and (_sfx_pl[n] as AudioStreamPlayer).stream != null:
		(_sfx_pl[n] as AudioStreamPlayer).play()

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
		for tmi in real.find_children("*", "MeshInstance3D", true, false):
			var tm := tmi as MeshInstance3D
			tm.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			for s in range(tm.mesh.get_surface_count()):
				var sm := tm.mesh.surface_get_material(s)
				if sm is StandardMaterial3D:
					var d := (sm as StandardMaterial3D).duplicate() as StandardMaterial3D
					d.metallic = 0.0; d.roughness = 1.0; d.metallic_specular = 0.1; d.vertex_color_use_as_albedo = false
					tm.set_surface_override_material(s, d)
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
	_eng.pitch_scale = 0.7 + _throttle * 0.45 + _speed / 700.0
	_lock_cd -= dt
	if _lock_cd <= 0.0 and not _won and not _target().is_empty():
		_sfx("aggancio"); _lock_cd = 0.45
	if _fxtest and _frame == 12:
		_boom(_player.position + -_player.basis.z * 260.0 + Vector3(0, 6, 0), 1.6)
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
			_ammo -= 1; _fire_cd = 0.35; _sfx("lancio")
			_missiles.append({"p": _player.position + -_player.basis.z * 6.0, "v": -_player.basis.z * (_speed + 350.0),
				"t": _target(), "life": 7.0, "node": _make_missile()})
		if e.keycode == KEY_R: _reset()
		if e.keycode == KEY_C: _cockpit = not _cockpit
		if e.keycode == KEY_G: _q = (_q + 1) % 3; _apply_quality()
		if e.keycode == KEY_N and _tracks.size() > 0: _play_track(_ti + 1)
		if e.keycode == KEY_MINUS or e.keycode == KEY_KP_SUBTRACT: _cz = minf(_cz * 1.15, 4.0)   # camera piu' lontana
		if e.keycode == KEY_EQUAL or e.keycode == KEY_KP_ADD: _cz = maxf(_cz / 1.15, 0.4)       # camera piu' vicina
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
		ms["pt"] = float(ms.get("pt", 0.0)) - dt                      # scia: puffi piccoli (riga 3 del foglio) ogni 0,03 s
		if ms["pt"] <= 0.0:
			_fx_quad(ms["p"], 7.0, 3, 2, 0.5, true); ms["pt"] = 0.03
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

## Esplosioni: fotogrammi originali (entry 2, foglio 256 px, 4 colonne x 3 righe utili), fusione additiva, sempre rivolte alla camera
var _fx_tex: Texture2D
func _fx_texture() -> Texture2D:
	if _fx_tex == null:
		var img := Image.load_from_file(ProjectSettings.globalize_path("res://assets/fx/explosion.png"))
		if img != null:
			_fx_tex = ImageTexture.create_from_image(img)
	return _fx_tex

func _fx_quad(p: Vector3, size: float, row0: int, frames: int, life: float, fade: bool) -> void:
	var tex := _fx_texture()
	if tex == null:
		push_warning("fx: texture esplosione non caricata (assets/fx/explosion.png)")
		return
	var m := MeshInstance3D.new(); var q := QuadMesh.new(); q.size = Vector2(size, size); m.mesh = q
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED; mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	mat.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED; mat.cull_mode = BaseMaterial3D.CULL_DISABLED; mat.albedo_texture = tex
	mat.texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST; mat.no_depth_test = false
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA   # senza, la fusione additiva viene ignorata
	mat.uv1_scale = Vector3(0.25, 56.0 / 224.0, 1.0)
	m.material_override = mat; m.position = p; m.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF; add_child(m)
	_fx.append({"n": m, "t": 0.0, "mat": mat, "row0": row0, "frames": frames, "life": life, "fade": fade})

func _boom(p: Vector3, s: float) -> void:
	_sfx("esplosione")
	_fx_quad(p, 38.0 * s, 0, 12, 0.9, false)

func _update_fx(dt: float) -> void:
	for i in range(_fx.size() - 1, -1, -1):
		var f: Dictionary = _fx[i]; f["t"] = float(f["t"]) + dt
		var k := float(f["t"]) / float(f["life"])
		if k >= 1.0:
			(f["n"] as Node3D).queue_free(); _fx.remove_at(i); continue
		var fr := int(k * int(f["frames"])); var idx := int(f["row0"]) * 4 + fr
		var mat: StandardMaterial3D = f["mat"]
		mat.uv1_offset = Vector3((idx % 4) * 0.25, (idx / 4) * (56.0 / 224.0), 0.0)
		if f["fade"]:
			var c := 1.0 - k; mat.albedo_color = Color(c, c, c)

func _hud_data(fwd_sign: float, spd: float) -> Dictionary:
	var b := _player.basis
	var f := b.z * fwd_sign * -1.0 if fwd_sign < 0 else b.z
	var fwd := -b.z if fwd_sign < 0 else b.z               # direzione "avanti" dell'aereo
	var blips: Array = []
	var tgt: Dictionary = _target() if fwd_sign < 0 else {}
	for u in _units:
		if u["alive"] and u["enemy"]:
			var rel: Vector3 = (u["node"] as Node3D).position - _player.position
			var loc := b.inverse() * rel
			blips.append([loc.x * (1.0 if fwd_sign < 0 else -1.0), (-loc.z) if fwd_sign < 0 else loc.z])
	var td := {}
	if not tgt.is_empty():
		var tp: Vector3 = (tgt["node"] as Node3D).position
		if not _cam.is_position_behind(tp):
			td = {"screen": _cam.unproject_position(tp), "dist": (tp - _player.position).length() / WS * WS}
	return {"speed": spd * 3.6, "alt": _player.position.y - ground_m(_player.position), "thr": clampf(_throttle / 1.4, 0, 1),
		"ammo": _ammo, "enemies": _enemies_left(), "pitch": asin(clampf(fwd.y, -1, 1)), "roll": atan2(b.x.y, b.y.y) * (1.0 if fwd_sign < 0 else -1.0),
		"heading": rad_to_deg(atan2(fwd.x, fwd.z)), "blips": blips, "radar_range": 4000.0, "target": td, "cockpit": _cockpit, "damage": 0}

func _update_cam(dt: float) -> void:
	if _cockpit:
		_player.visible = false
		_cam.fov = 78.0
		_cam.position = _player.position + _player.basis * Vector3(0, 0.9, -2.4)
		_cam.basis = _player.basis
		return
	_player.visible = true
	var k := clampf(_speed / 210.0, 0.0, 1.0)                        # distanza e campo visivo crescono con la velocita'
	_cam.fov = lerpf(62.0, 74.0, k)
	var want := _player.position + _player.basis * Vector3(0, lerpf(1.6, 2.2, k) * _cz, lerpf(5.2, 7.0, k) * _cz)
	_cam.position = want   # nessun ritardo sulla posizione: con il lerp la camera restava indietro di velocita/6 metri
	_cam.look_at(_player.position + _player.basis * Vector3(0, 0.6, -8.0), _player.basis.y)

func _update_hud() -> void:
	_hud2.d = _hud_data(-1.0, _speed); _hud2.queue_redraw()
	var alt := _player.position.y - ground_m(_player.position)
	var t := _target()
	_hud.text = "FPS %d  qualita' %s (G)   Su/Giu beccheggio  Sx/Dx virata  A/D imbardata  W/S motore  Spazio missile  C camera  +/- distanza  N musica (%s)  R ricomincia" % [Engine.get_frames_per_second(), ["bassa", "media", "alta"][_q], (_tracks[_ti].get_basename() if _tracks.size() > 0 else "nessuna")]
	_hud.position = Vector2(14, 70); _hud.add_theme_font_size_override("font_size", 14); _hud.modulate = Color(1, 1, 1, 0.6)
