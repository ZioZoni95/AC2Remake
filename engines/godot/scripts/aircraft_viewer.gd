extends Node3D
## Visualizzatore di un aereo di Ace Combat 2 (glTF estratto dal disco con pipeline/ac2_aircraft.py).
## DUE MODALITA' (tasto M): PS1 = fedele all'originale (texture a pixel netti, colori vertice come luce);
## MODERNA = stesse mesh e texture ma filtrate, luci e ombre reali, normali morbide, cielo e post-elaborazione.
## Argomenti dopo `--`: --model=res://assets/aerei/xfa27.gltf  --mode=psx|modern
## Comandi: frecce = orbita, rotella/+/- = zoom, Spazio = pausa rotazione, M = modalita', Esc = esci.

@export var model_path: String = "res://assets/aerei/xfa27.gltf"
@export var modern := true
@export var auto_orbit := true

var _pivot := Node3D.new()
var _cam := Camera3D.new()
var _env := WorldEnvironment.new()
var _sun := DirectionalLight3D.new()
var _psx: Node
var _mod: Node
var _yaw := 2.4
var _pitch := -0.25
var _dist := 5.0
var _label := Label.new()

func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--model="): model_path = a.substr(8)
		if a.begins_with("--mode="): modern = (a.substr(7) == "modern")
	add_child(_env)
	add_child(_sun)
	add_child(_pivot)
	_pivot.add_child(_cam)
	_cam.current = true
	_cam.fov = 40.0
	_psx = _load_model(model_path)
	_mod = _load_model(model_path)
	if _psx == null or _mod == null:
		return
	_psx_style(_psx)
	_modern_style(_mod)
	add_child(_psx)   # i modelli restano fermi: orbita solo la camera (figlia del pivot)
	add_child(_mod)
	_frame(_psx)
	_mod.position = _psx.position
	var layer := CanvasLayer.new()
	add_child(layer)
	_label.position = Vector2(12, 8)
	layer.add_child(_label)
	_apply_mode()
	_update_cam()

func _load_model(path: String) -> Node:
	var doc := GLTFDocument.new()
	var state := GLTFState.new()
	var err := doc.append_from_file(ProjectSettings.globalize_path(path), state)
	if err != OK:
		push_error("glTF non caricato (%s): errore %d. Hai eseguito tools/sync_godot_assets.sh?" % [path, err])
		_label.text = "MODELLO NON TROVATO: " + path
		return null
	return doc.generate_scene(state)

func _apply_mode() -> void:
	_psx.visible = not modern
	_mod.visible = modern
	_sun.visible = modern
	var e := Environment.new()
	if modern:
		var sky := Sky.new()
		var pm := ProceduralSkyMaterial.new()
		pm.sky_top_color = Color(0.22, 0.42, 0.78)
		pm.sky_horizon_color = Color(0.70, 0.78, 0.88)
		pm.ground_horizon_color = Color(0.55, 0.58, 0.62)
		pm.ground_bottom_color = Color(0.18, 0.20, 0.24)
		sky.sky_material = pm
		e.background_mode = Environment.BG_SKY
		e.sky = sky
		e.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
		e.tonemap_mode = Environment.TONE_MAPPER_FILMIC
		e.glow_enabled = true
		e.glow_intensity = 0.5
		e.ssao_enabled = true
		_sun.rotation_degrees = Vector3(-45, 35, 0)
		_sun.light_energy = 1.4
		_sun.shadow_enabled = true
	else:
		e.background_mode = Environment.BG_COLOR
		e.background_color = Color(0.09, 0.11, 0.16)
	_env.environment = e
	_label.text = "%s  [%s]  M = cambia modalita'" % [model_path.get_file(), "MODERNA" if modern else "PS1 fedele"]

## PS1: texture a pixel netti, colori vertice come luce (gia' "cotta"), niente ombre.
func _psx_style(n: Node) -> void:
	for mi in n.find_children("*", "MeshInstance3D", true, false):
		var m := mi as MeshInstance3D
		for s in range(m.mesh.get_surface_count()):
			var sm := m.mesh.surface_get_material(s)
			if sm is StandardMaterial3D:
				var d := (sm as StandardMaterial3D).duplicate() as StandardMaterial3D
				d.texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST
				d.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
				d.vertex_color_use_as_albedo = true
				m.set_surface_override_material(s, d)

## Moderna: stessa geometria e texture, ma normali morbide, filtro con mipmap, materiale lucido e luce reale.
func _modern_style(n: Node) -> void:
	for mi in n.find_children("*", "MeshInstance3D", true, false):
		var m := mi as MeshInstance3D
		var out := ArrayMesh.new()
		for s in range(m.mesh.get_surface_count()):
			var st := SurfaceTool.new()
			st.create_from(m.mesh, s)
			if not model_path.contains("_smooth"):   # i file *_smooth* hanno gia' le normali morbide
				st.generate_normals()
			out = st.commit(out)
			var sm := m.mesh.surface_get_material(s)
			if sm is StandardMaterial3D:
				var d := (sm as StandardMaterial3D).duplicate() as StandardMaterial3D
				d.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
				d.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL
				d.vertex_color_use_as_albedo = false
				d.metallic = 0.45
				d.roughness = 0.4
				d.metallic_specular = 0.6
				out.surface_set_material(out.get_surface_count() - 1, d)
		m.mesh = out

func _frame(n: Node3D) -> void:
	var box := AABB()
	var first := true
	for mi in n.find_children("*", "MeshInstance3D", true, false):
		var b := (mi as MeshInstance3D).get_aabb()
		box = b if first else box.merge(b)
		first = false
	if not first:
		n.position = -box.get_center()
		_dist = max(box.size.length() * 1.15, 1.0)

func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventKey and e.pressed:
		match e.keycode:
			KEY_LEFT: _yaw -= 0.1
			KEY_RIGHT: _yaw += 0.1
			KEY_UP: _pitch = clamp(_pitch + 0.1, -1.4, 1.4)
			KEY_DOWN: _pitch = clamp(_pitch - 0.1, -1.4, 1.4)
			KEY_EQUAL, KEY_KP_ADD: _dist *= 0.9
			KEY_MINUS, KEY_KP_SUBTRACT: _dist *= 1.1
			KEY_SPACE: auto_orbit = not auto_orbit
			KEY_M:
				modern = not modern
				_apply_mode()
			KEY_ESCAPE: get_tree().quit()
	if e is InputEventMouseButton and e.pressed:
		if e.button_index == MOUSE_BUTTON_WHEEL_UP: _dist *= 0.9
		if e.button_index == MOUSE_BUTTON_WHEEL_DOWN: _dist *= 1.1
	_update_cam()

func _process(dt: float) -> void:
	if auto_orbit:
		_yaw += dt * 0.5
	_update_cam()

func _update_cam() -> void:
	_cam.position = Vector3(0, 0, _dist)
	_pivot.rotation = Vector3(_pitch, _yaw, 0)
