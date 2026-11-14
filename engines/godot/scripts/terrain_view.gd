extends Node3D
## Terreno di Fighter's Honor ridisegnato dai poligoni e dalle texture originali delle tessere (SCOPERTE #32).
## Due modalita' (M): PS1 fedele (originale, a pixel netti) / moderna (texture 4x Real-ESRGAN, luce con ombre, SSAO, cielo, nebbia). Argomento: --mode=psx|modern.
## Comandi: WASD = muovi, Q/E = giu'/su, tasto destro + mouse = guarda, Maiusc = veloce, rotella = velocita', Esc = esci.
## Argomenti dopo `--`: --cam=x,y,z,yaw,pitch (metri e gradi) per posizionare la camera (utile per le catture).
var _cam := Camera3D.new()
var _speed := 120.0
var _yaw := 0.0
var _pitch := -0.5

var _modern := true
var _env := WorldEnvironment.new()
var _sun := DirectionalLight3D.new()
var _psx: Node3D
var _mod: Node3D

func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--mode="): _modern = (a.substr(7) == "modern")
	add_child(_env); add_child(_sun)
	_sun.rotation_degrees = Vector3(-38, 40, 0); _sun.shadow_enabled = true; _sun.directional_shadow_max_distance = 3000.0; _sun.light_energy = 1.6
	_psx = _load("res://assets/fighters_honor/terreno_mesh.gltf", false)
	_mod = _load("res://assets/fighters_honor/terreno_mesh_hd.gltf", true)
	if _psx: add_child(_psx)
	if _mod: add_child(_mod)
	_cam.position = Vector3(-900, 260, -2400); _cam.far = 20000.0; _cam.fov = 70.0; _cam.current = true
	add_child(_cam)
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--cam="):
			var v := a.substr(6).split(",")
			_cam.position = Vector3(float(v[0]), float(v[1]), float(v[2])); _yaw = deg_to_rad(float(v[3])); _pitch = deg_to_rad(float(v[4]))
	_mode()
	_apply()

func _load(path: String, modern: bool) -> Node3D:
	var doc := GLTFDocument.new(); var st := GLTFState.new()
	if doc.append_from_file(ProjectSettings.globalize_path(path), st) != OK:
		push_error("non trovato: " + path + " (ac2_terrain.py mesh, upscale_gltf.py, tools/sync_godot_assets.sh)"); return null
	var root := doc.generate_scene(st) as Node3D
	for mi in root.find_children("*", "MeshInstance3D", true, false):
		var m := mi as MeshInstance3D
		for s in range(m.mesh.get_surface_count()):
			var sm := m.mesh.surface_get_material(s)
			if sm is StandardMaterial3D:
				var d := (sm as StandardMaterial3D).duplicate() as StandardMaterial3D
				d.vertex_color_use_as_albedo = false; d.cull_mode = BaseMaterial3D.CULL_DISABLED
				if modern:
					d.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
					d.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL; d.roughness = 0.92; d.metallic = 0.0
				else:
					d.texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST
					d.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
				if OS.get_cmdline_user_args().has("--flat"):   # diagnostica: grigio uniforme senza texture
					d = StandardMaterial3D.new(); d.albedo_color = Color(0.45, 0.45, 0.45); d.cull_mode = BaseMaterial3D.CULL_DISABLED
				m.set_surface_override_material(s, d)
	return root

func _mode() -> void:
	if _psx: _psx.visible = not _modern
	if _mod: _mod.visible = _modern
	_sun.visible = _modern
	var e := Environment.new()
	if _modern:
		var sky := Sky.new(); var pm := ProceduralSkyMaterial.new()
		pm.sky_top_color = Color(0.20, 0.40, 0.78); pm.sky_horizon_color = Color(0.74, 0.82, 0.92)
		pm.ground_horizon_color = Color(0.55, 0.58, 0.55)
		sky.sky_material = pm
		e.background_mode = Environment.BG_SKY; e.sky = sky
		e.ambient_light_source = Environment.AMBIENT_SOURCE_SKY; e.ambient_light_energy = 0.6
		e.tonemap_mode = Environment.TONE_MAPPER_FILMIC
		e.fog_enabled = true; e.fog_density = 0.00012; e.fog_light_color = Color(0.70, 0.78, 0.90)
		e.ssao_enabled = true; e.glow_enabled = true; e.glow_intensity = 0.4
	else:
		e.background_mode = Environment.BG_COLOR; e.background_color = Color(0.09, 0.11, 0.16)
	_env.environment = e

func _apply() -> void:
	_cam.rotation = Vector3(_pitch, _yaw, 0)

func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT):
		_yaw -= e.relative.x * 0.004; _pitch = clamp(_pitch - e.relative.y * 0.004, -1.5, 1.5)
	if e is InputEventMouseButton and e.pressed:
		if e.button_index == MOUSE_BUTTON_WHEEL_UP: _speed *= 1.2
		if e.button_index == MOUSE_BUTTON_WHEEL_DOWN: _speed /= 1.2
	if e is InputEventKey and e.pressed:
		if e.keycode == KEY_ESCAPE: get_tree().quit()
		if e.keycode == KEY_M: _modern = not _modern; _mode()

func _process(dt: float) -> void:
	var v := Vector3.ZERO
	if Input.is_key_pressed(KEY_W): v.z -= 1
	if Input.is_key_pressed(KEY_S): v.z += 1
	if Input.is_key_pressed(KEY_A): v.x -= 1
	if Input.is_key_pressed(KEY_D): v.x += 1
	if Input.is_key_pressed(KEY_E): v.y += 1
	if Input.is_key_pressed(KEY_Q): v.y -= 1
	_cam.position += _cam.global_transform.basis * v * _speed * (4.0 if Input.is_key_pressed(KEY_SHIFT) else 1.0) * dt
	_apply()
