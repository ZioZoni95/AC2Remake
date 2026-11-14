extends "res://scripts/flight_demo.gd"
## VISTA DAL VIVO: il gioco originale gira nell'emulatore (codice, IA, fisica e script originali) e a ogni fotogramma scrive lo
## stato in /tmp/ac2_state.bin (pipeline/lua/ac2_remote.lua con AC2_EXPORT=1); Godot lo legge e disegna con i modelli moderni.
## Layout: [u32 frame][oggetto giocatore 0x3f8 B][63 slot x 0x174 B][camera 0x60 B]; posizione = parole 9..11 / 2048,
## angoli = parole 13..15 (4096 = giro): beccheggio (salita +), imbardata (0 = +Z, verso +X), rollio (segno da verificare).
## Si pilota nella finestra dell'emulatore (tastiera: WASD croce, Z, C, X ...). Esc = esci.

const STATE := "/tmp/ac2_state.bin"
const PL_SIZE := 0x3f8
const SLOT_SIZE := 0x174
var _last_frame := -1
var _prev_pos := Vector3.ZERO
var _vel := 0.0
var _roll_sign := -1.0

func _ready() -> void:
	super._ready()
	if _player.get_child_count() > 0:
		(_player.get_child(0) as Node3D).rotation.y = 0.0   # qui il naso (+Z) e' gia' la direzione di avanti
	_hud.text = "In attesa dello stato dal gioco (/tmp/ac2_state.bin)..."

func _pose(buf: PackedByteArray, base: int) -> Array:
	var p := Vector3(buf.decode_s32(base + 36) / 2048.0, buf.decode_s32(base + 40) / 2048.0, buf.decode_s32(base + 44) / 2048.0)
	var pitch := buf.decode_s32(base + 52) * TAU / 4096.0
	var yaw := buf.decode_s32(base + 56) * TAU / 4096.0
	var roll := buf.decode_s32(base + 60) * TAU / 4096.0
	var g := Vector3(p.x * WS, -p.y * WS, p.z * WS)
	var f := Vector3(cos(pitch) * sin(yaw), sin(pitch), cos(pitch) * cos(yaw)).normalized()
	var xa := Vector3.UP.cross(f).normalized()
	var ya := f.cross(xa)
	var b := Basis(xa, ya, f).rotated(f, _roll_sign * roll)
	return [g, b]

func _process(dt: float) -> void:
	if not FileAccess.file_exists(STATE):
		return
	var f := FileAccess.open(STATE, FileAccess.READ)
	if f == null:
		return
	var buf := f.get_buffer(4 + PL_SIZE + 63 * SLOT_SIZE + 0x60)
	if buf.size() < 4 + PL_SIZE + 63 * SLOT_SIZE:
		return
	var frame := buf.decode_u32(0)
	if frame == _last_frame:
		return
	var gdt := (frame - _last_frame) / 50.0 if _last_frame >= 0 else 0.0   # il gioco PAL gira a 50 Hz
	_last_frame = frame
	var pl := _pose(buf, 4)
	var newp: Vector3 = pl[0]
	if gdt > 0.0 and gdt < 1.0:
		_vel = lerpf(_vel, (newp - _prev_pos).length() / gdt, 0.2)
	_prev_pos = newp
	_player.position = newp
	_player.basis = pl[1]
	for u in _units:
		var base := 4 + PL_SIZE + int(u["slot"]) * SLOT_SIZE
		var node: Node3D = u["node"]
		var live := buf.decode_u32(base) != 0
		node.visible = live
		if live:
			var q := _pose(buf, base)
			node.position = q[0]
			node.basis = (q[1] as Basis).scaled(Vector3.ONE * MODEL_SCALE)
	var fwd := (pl[1] as Basis).z
	var want := newp - fwd * 11.0 + Vector3.UP * 3.2
	_cam.position = _cam.position.lerp(want, clampf(dt * 8.0, 0, 1))
	_cam.look_at(newp + fwd * 14.0, Vector3.UP)
	_hud.text = "ORIGINALE dal vivo  frame %d   VEL %d km/h   QUOTA %d m   pos (%d, %d, %d)\nIl gioco gira nell'emulatore: pilota li (WASD/Z/C/X). Esc esce." % [
		frame, int(_vel * 3.6), int(newp.y), int(newp.x / WS), int(-newp.y / WS), int(newp.z / WS)]
