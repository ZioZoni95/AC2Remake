extends Node3D
## Visualizzatore della missione Fighter's Honor: unita' nelle posizioni lette dalla RAM del gioco (SCOPERTE #25-#26),
## ciascuna col modello del suo tipo (parola 1 dello slot -> models/unita_{3t+2}.gltf), il giocatore (XFA-27) e i punti
## di piazzamento della tabella T2. Dati: res://assets/fighters_honor/mission.json (tools/sync_godot_assets.sh).
## SCALA: 0.01 m per unita' di mondo e' un'IPOTESI (le distanze reali tra unita' sono da verificare col gioco).
## Comandi: WASD = muovi, Q/E = giu'/su, tasto destro + mouse = guarda, Maiusc = veloce, rotella = velocita',
## [ ] = ingrandimento modelli (solo per vederli), L = etichette, T = punti T2, P = mostra i segnaposto parcheggiati, Esc = esci.
## Argomenti dopo `--`: --cam=overview|player

const DIR := "res://assets/fighters_honor/"
const SCALE := 0.01

var _mag := 25.0          # ingrandimento dei modelli rispetto alla scala di mondo (solo per vederli)
var _units: Array = []
var _cam := Camera3D.new()
var _speed := 600.0
var _yaw := 0.0
var _pitch := -0.35
var _labels: Array = []
var _t2: Array = []
var _parked: Array = []
var _cache := {}
var _info := Label.new()

func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	var sky := Sky.new(); var pm := ProceduralSkyMaterial.new()
	pm.sky_top_color = Color(0.22, 0.42, 0.78); pm.sky_horizon_color = Color(0.70, 0.78, 0.88)
	pm.ground_horizon_color = Color(0.45, 0.50, 0.45); pm.ground_bottom_color = Color(0.20, 0.24, 0.20)
	sky.sky_material = pm
	env.environment.background_mode = Environment.BG_SKY
	env.environment.sky = sky
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	add_child(env)
	var sun := DirectionalLight3D.new(); sun.rotation_degrees = Vector3(-50, 30, 0); sun.shadow_enabled = true
	add_child(sun)
	# suolo di riferimento a quota 0 (il terreno vero e' da decodificare)
	var ground := MeshInstance3D.new(); var pl := PlaneMesh.new(); pl.size = Vector2(8000, 8000)
	ground.mesh = pl
	var gm := StandardMaterial3D.new(); gm.albedo_color = Color(0.32, 0.38, 0.30); ground.material_override = gm
	add_child(ground)
	add_child(_cam); _cam.current = true; _cam.fov = 60.0; _cam.far = 20000.0
	var layer := CanvasLayer.new(); add_child(layer); _info.position = Vector2(12, 8); layer.add_child(_info)

	var f := FileAccess.open(DIR + "mission.json", FileAccess.READ)
	if f == null:
		_info.text = "mission.json non trovato: esegui ac2_export_godot.py e tools/sync_godot_assets.sh"
		return
	var d: Dictionary = JSON.parse_string(f.get_as_text())
	var n := 0
	var min_p := Vector3(1e9, 1e9, 1e9); var max_p := Vector3(-1e9, -1e9, -1e9)
	for u in d["unita"]:
		var p := _w2g(u["pos"])
		var node := _make_unit(int(u["tipo"]))
		node.position = p
		node.scale = Vector3.ONE * _mag
		add_child(node); _units.append(node)
		var lb := Label3D.new(); lb.text = "#%d c%d s%d t%d" % [u["slot"], u["categoria"], u["squadra"], u["tipo"]]
		lb.billboard = BaseMaterial3D.BILLBOARD_ENABLED; lb.pixel_size = 0.02; lb.position = p + Vector3(0, 6, 0)
		lb.no_depth_test = true; add_child(lb); _labels.append(lb)
		n += 1; min_p = min_p.min(p); max_p = max_p.max(p)
	var pp := _w2g(d["giocatore"]["pos"])
	var pj := _load_model("res://assets/aerei/xfa27_smooth1_hd.gltf")
	if pj != null:
		pj.position = pp; pj.scale = Vector3.ONE * _mag; add_child(pj); _units.append(pj)
	for q in d["piazzamento_T2"]:
		var m := MeshInstance3D.new(); var sm := SphereMesh.new(); sm.radius = 12.0; sm.height = 24.0; m.mesh = sm
		var mm := StandardMaterial3D.new(); mm.albedo_color = Color(1, 0.9, 0.2); mm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		m.material_override = mm; m.position = _w2g(q); add_child(m); _t2.append(m)
	min_p = min_p.min(pp); max_p = max_p.max(pp)
	var center := (min_p + max_p) / 2.0
	var ext: float = max((max_p - min_p).length(), 50.0)
	var mode := "overview"
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--cam="): mode = a.substr(6)
	if mode == "player":
		_cam.position = pp + Vector3(0, 8, 25); _yaw = 0.0; _pitch = -0.15
	else:
		_cam.position = center + Vector3(0, ext * 0.55, ext * 0.75); _yaw = 0.0; _pitch = -0.6
		_speed = ext * 0.6
	_info.text = "Fighter's Honor — %d unita' dalla T1 (etichetta: #slot categoria squadra tipo), %d punti T2 | WASD/QE, tasto destro = guarda, L etichette, T punti T2, [ ] ingrandimento" % [n, _t2.size()]
	_apply_cam()

## coordinate di mondo (x, y verso il basso, z) -> Godot (y verso l'alto), scala ipotetica
func _w2g(p: Array) -> Vector3:
	return Vector3(p[0] * SCALE, -p[1] * SCALE, p[2] * SCALE)

func _make_unit(t: int) -> Node3D:
	var path := DIR + "unita_%02d.gltf" % (3 * clampi(t, 0, 12) + 2)
	if not _cache.has(path):
		_cache[path] = _load_model(path)
	var tmpl: Node = _cache[path]
	if tmpl == null:
		var s := MeshInstance3D.new(); s.mesh = BoxMesh.new(); return s
	return tmpl.duplicate() as Node3D

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
				var d := (sm as StandardMaterial3D).duplicate() as StandardMaterial3D
				d.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
				d.vertex_color_use_as_albedo = false; d.metallic = 0.3; d.roughness = 0.5
				m.set_surface_override_material(s, d)
	return root

func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT):
		_yaw -= e.relative.x * 0.004; _pitch = clamp(_pitch - e.relative.y * 0.004, -1.5, 1.5)
	if e is InputEventMouseButton and e.pressed:
		if e.button_index == MOUSE_BUTTON_WHEEL_UP: _speed *= 1.2
		if e.button_index == MOUSE_BUTTON_WHEEL_DOWN: _speed /= 1.2
	if e is InputEventKey and e.pressed:
		match e.keycode:
			KEY_BRACKETRIGHT: _mag *= 1.5; _rescale()
			KEY_BRACKETLEFT: _mag /= 1.5; _rescale()
			KEY_L: for l in _labels: l.visible = not l.visible
			KEY_T: for m in _t2: m.visible = not m.visible
			KEY_P: for x in _parked: x.visible = not x.visible
			KEY_ESCAPE: get_tree().quit()

func _rescale() -> void:
	for u in _units:
		(u as Node3D).scale = Vector3.ONE * _mag

func _process(dt: float) -> void:
	var v := Vector3.ZERO
	if Input.is_key_pressed(KEY_W): v.z -= 1
	if Input.is_key_pressed(KEY_S): v.z += 1
	if Input.is_key_pressed(KEY_A): v.x -= 1
	if Input.is_key_pressed(KEY_D): v.x += 1
	if Input.is_key_pressed(KEY_E): v.y += 1
	if Input.is_key_pressed(KEY_Q): v.y -= 1
	var s := _speed * (4.0 if Input.is_key_pressed(KEY_SHIFT) else 1.0)
	_cam.position += _cam.global_transform.basis * v * s * dt
	_apply_cam()

func _apply_cam() -> void:
	_cam.rotation = Vector3(_pitch, _yaw, 0)
