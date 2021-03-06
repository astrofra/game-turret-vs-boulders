import harfang as hg
from os import path
from math import radians, cos, sin
from random import uniform, randint
from constants import *

hg.LoadPlugins()


def rvect(r):
	return hg.Vector3(uniform(-r, r), uniform(-r, r), uniform(-r, r))


def setup_game_level(plus=None):
	scn = plus.NewScene()

	while not scn.IsReady():
		plus.UpdateScene(scn, plus.UpdateClock())

	scn.GetPhysicSystem().SetDebugVisuals(False)

	# Create a camera
	cam_matrix = hg.Matrix4.TransformationMatrix(hg.Vector3(0, 15, 3), hg.Vector3(radians(90), 0, 0))
	cam = plus.AddCamera(scn, cam_matrix)

	# Ambient Occlusion
	pp_sao = hg.SAOPostProcess()
	cam.AddComponent(pp_sao)
	pp_sao.SetStrength(0.35)
	pp_sao.SetStrength(0.35)
	pp_sao.SetRadius(15.0)
	pp_sao.SetSampleCount(8)

	plus.AddLight(scn, hg.Matrix4.TransformationMatrix(hg.Vector3(-10, 10, 5), hg.Vector3(radians(55), radians(100), 0)), hg.LightModelSpot, 40.0, True)
	env_blue = hg.Color.Blue + hg.Color.Green * 0.5
	plus.AddLight(scn, hg.Matrix4.TranslationMatrix(hg.Vector3(10, -25, -5)), hg.LightModelPoint, 0.0, False, env_blue, hg.Color.Black)
	plus.AddEnvironment(scn, hg.Color.Black, env_blue * 0.35)
	ground = plus.AddPhysicPlane(scn)

	return scn, ground


def create_turret(plus=None, scn=None, pos=hg.Vector3(0, 0.75, 0), rot=hg.Vector3(), w=1, h=1.25, d=1, mass = 10):
	scn.GetPhysicSystem().SetForceRigidBodyAxisLockOnCreation(hg.AxisLockX + hg.AxisLockY + hg.AxisLockZ + hg.AxisLockRotX + hg.AxisLockRotZ)
	root = plus.AddPhysicCube(scn, hg.Matrix4.TransformationMatrix(pos, rot), w, h, d, mass)
	root[0].SetName('turret')
	root[1].SetAngularDamping(1.0)
	cannon_geo = plus.CreateGeometry(plus.CreateCylinder(w * 0.25, d))
	cannon = plus.AddObject(scn, cannon_geo, hg.Matrix4.TransformationMatrix(hg.Vector3(0, h * 0.2, d * 0.75),
																			 hg.Vector3(radians(90), 0, 0)))
	cannon.GetTransform().SetParent(root[0])

	return root, cannon, mass


def rotate_turret(turret, angle, mass):
	rot = turret[0].GetTransform().GetRotation()
	dt_rot = radians(angle) - rot.y
	turret[1].SetIsSleeping(False)
	turret[1].ApplyTorque(hg.Vector3(0, dt_rot * mass * turret_rotation_speed, 0))


def spawn_enemy(plus, scn, pos = hg.Vector3(0, 2, 5)):
	scn.GetPhysicSystem().SetForceRigidBodyAxisLockOnCreation(0)
	root = plus.AddPhysicSphere(scn, hg.Matrix4.TranslationMatrix(pos), 0.7, 6, 16, enemy_mass, "assets/materials/green.mat")
	root[0].SetName('enemy')

	return root


def throw_bullet(plus, scn, pos, dir):
	scn.GetPhysicSystem().SetForceRigidBodyAxisLockOnCreation(hg.AxisLockY)
	root = plus.AddPhysicSphere(scn, hg.Matrix4.TranslationMatrix(pos), 0.2, 3, 8, 1.0, "assets/materials/grey.mat")
	root[0].SetName('bullet')
	root[1].ApplyLinearImpulse(dir * bullet_velocity)

	return root


def destroy_enemy(plus, scn, enemy):
	scn.RemoveNode(enemy)


def render_aim_cursor(plus, scn, angle):
	radius = screen_width / 8
	angle = 90 - angle
	a = hg.Vector2(cos(radians(angle)), sin(radians(angle))) * radius * 1.15
	b = hg.Vector2(cos(radians(angle - 5)), sin(radians(angle - 5))) * radius
	c = hg.Vector2(cos(radians(angle + 5)), sin(radians(angle + 5))) * radius
	plus.Triangle2D(screen_width * 0.5 + a.x, screen_height * 0.15 + a.y,
					screen_width * 0.5 + b.x, screen_height * 0.15 + b.y,
					screen_width * 0.5 + c.x, screen_height * 0.15 + c.y,
					hg.Color.Green, hg.Color.Green, hg.Color.Green)


def display_hud(plus, player_energy, cool_down, score):

	# Life bar
	plus.Quad2D(screen_width * 0.015, screen_height * 0.225,
				player_energy * screen_width * 0.15, screen_height * 0.225,
				player_energy * screen_width * 0.15, screen_height * 0.175,
				screen_width * 0.015, screen_height * 0.175,
				hg.Color.Green, hg.Color.Green, hg.Color.Green, hg.Color.Green)
	plus.Text2D(screen_width * 0.018, screen_height * 0.1825, "LIFE", font_size, hg.Color.White, screen_font)

	plus.Quad2D(screen_width * 0.015, screen_height * 0.15,
				cool_down * screen_width * 0.15, screen_height * 0.15,
				cool_down * screen_width * 0.15, screen_height * 0.1,
				screen_width * 0.015, screen_height * 0.1,
				hg.Color.Green, hg.Color.Green, hg.Color.Green, hg.Color.Green)

	plus.Text2D(screen_width * 0.018, screen_height * 0.1075, "HEAT", font_size, hg.Color.White, screen_font)

	plus.Text2D(screen_width * 0.018, screen_height * 0.035, "SCORE", font_size, hg.Color.White, screen_font)
	plus.Text2D(screen_width * 0.15, screen_height * 0.035, str(score), font_size, hg.Color.Green, screen_font)


def create_explosion(plus, scn, pos, debris_amount=32, debris_radius=0.5):
	scn.GetPhysicSystem().SetForceRigidBodyAxisLockOnCreation(0)
	new_debris_list = []
	for i in range(debris_amount):
		debris_size = uniform(0.1, 0.25)
		debris = plus.AddPhysicCube(scn, hg.Matrix4().TransformationMatrix(pos + rvect(debris_radius), rvect(radians(45))),
									debris_size, debris_size, debris_size, 0.05, "assets/materials/green.mat")
		debris[1].ApplyLinearImpulse(rvect(0.25))
		new_debris_list.append(debris[0])

	return new_debris_list


def play_sound_fx(mixer, sound_type):
	sounds = {'explosion': 4, 'hit': 4, 'shoot': 4, 'game_start': 1, 'game_over': 1, 'select': 1, 'error':1}
	if sound_type in sounds:
		sound_index = str(randint(0, sounds[sound_type] - 1))
		mixer.Start(mixer.LoadSound(path.join('assets', 'sfx', sound_type + '_' + sound_index + '.wav')))


def display_title_screen(plus, scn):
	plus.Text2D(screen_width * 0.15, screen_height * 0.625, "BOULDER\nATTACKS", font_size * 4.25, hg.Color(0,0,0,0.25), screen_font)
	plus.Text2D(screen_width * 0.15, screen_height * 0.65, "BOULDER\nATTACKS", font_size * 4.25, hg.Color.Green, screen_font)

	fade = abs(sin(hg.time_to_sec_f(plus.GetClock())))
	plus.Text2D(screen_width * 0.35, screen_height * 0.35, "PRESS SPACE", font_size * 1.25,
				hg.Color.Green * hg.Color(1, 1, 1, fade), screen_font)


def display_game_over(plus, scn, score):
	plus.Text2D(screen_width * 0.2, screen_height * 0.625, "GAME\n  OVER", font_size * 4.25, hg.Color(0,0,0,0.25), screen_font)
	plus.Text2D(screen_width * 0.2, screen_height * 0.65, "GAME\n  OVER", font_size * 4.25, hg.Color.Red, screen_font)

	plus.Text2D(screen_width * 0.3, screen_height * 0.35, "YOU SCORED " + str(score), font_size * 1.25,
				hg.Color.Red, screen_font)

	fade = abs(sin(hg.time_to_sec_f(plus.GetClock())))
	plus.Text2D(screen_width * 0.3, screen_height * 0.25, "PRESS SPACE", font_size * 1.25,
				hg.Color.Red * hg.Color(1, 1, 1, fade), screen_font)


def game():
	plus = hg.GetPlus()
	plus.RenderInit(screen_width, screen_height)
	al = hg.CreateMixer()
	al.Open()
	hg.MountFileDriver(hg.StdFileDriver())
	keyboard = hg.GetInputSystem().GetDevice("keyboard")

	scn, ground = setup_game_level(plus)
	turret, cannon, turret_mass = create_turret(plus, scn)

	game_state = "GAME_INIT"

	while not plus.IsAppEnded():
		dt = plus.UpdateClock()

		# Initialize Game
		if game_state == "GAME_INIT":
			enemy_list = []
			debris_list = []
			spawn_timer = 0.0
			turret_cool_down = 0.0
			enemy_spawn_interval = max_enemy_spawn_interval
			player_life = max_player_life
			target_angle = 0.0
			score = 0
			play_sound_fx(al, 'game_start')
			game_state = "TITLE"

		# Title screen
		if game_state == "TITLE":
			display_title_screen(plus, scn)
			if plus.KeyReleased(hg.KeySpace):
				game_state = "GAME"
		# Game
		elif game_state == "GAME":
			# Turret
			if plus.KeyDown(hg.KeyRight):
				target_angle += hg.time_to_sec_f(dt) * aim_rotation_speed
			else:
				if plus.KeyDown(hg.KeyLeft):
					target_angle -= hg.time_to_sec_f(dt) * aim_rotation_speed

			if plus.KeyPress(hg.KeySpace):
				if turret_cool_down < 0.0:
					throw_bullet(plus, scn, cannon.GetTransform().GetWorld().GetTranslation(), cannon.GetTransform().GetWorld().GetRow(1))
					turret_cool_down = turret_cool_down_duration
					play_sound_fx(al, 'shoot')
				else:
					play_sound_fx(al, 'error')
					turret_cool_down += 10.0 * hg.time_to_sec_f(dt)

			turret_cool_down -= hg.time_to_sec_f(dt)

			target_angle = max(min(target_angle, aim_angle_range['max']), aim_angle_range['min'])

			rotate_turret(turret, target_angle, turret_mass)

			# Enemies
			spawn_timer += hg.time_to_sec_f(dt)
			if spawn_timer > enemy_spawn_interval:
				spawn_timer = 0
				spawn_pos = hg.Vector3(uniform(-10, 10), 2.5, uniform(5.5, 6.5))
				spawn_pos.Normalize()
				spawn_pos *= 10.0
				spawn_pos.y = 5.0
				new_enemy = spawn_enemy(plus, scn, spawn_pos)
				enemy_list.append([new_enemy[0], new_enemy[1]])

			for enemy in enemy_list:
				# make enemy crawl toward the player
				enemy_dir = turret[0].GetTransform().GetPosition() - enemy[0].GetTransform().GetPosition()
				enemy_dir.Normalize()
				enemy[1].SetIsSleeping(False)
				enemy[1].ApplyLinearForce(enemy_dir * 0.25 * enemy_mass)

				col_pairs = scn.GetPhysicSystem().GetCollisionPairs(enemy[0])
				for col_pair in col_pairs:
					if 'turret' in [col_pair.GetNodeA().GetName(), col_pair.GetNodeB().GetName()]:
						destroy_enemy(plus, scn, enemy[0])
						debris_list.extend(create_explosion(plus, scn, enemy[0].GetTransform().GetPosition()))
						enemy_list.remove(enemy)
						play_sound_fx(al, 'explosion')
						play_sound_fx(al, 'hit')
						player_life -= 1
						turret_cool_down = 0.0
						if player_life < 1:
							play_sound_fx(al, 'game_over')
							game_state = "GAME_OVER"
					else:
						if 'bullet' in [col_pair.GetNodeA().GetName(), col_pair.GetNodeB().GetName()]:
							play_sound_fx(al, 'explosion')
							pos = col_pair.GetNodeB().GetTransform().GetPosition()
							debris_list.extend(create_explosion(plus, scn, pos, 8, 0.25))

							pos = enemy[0].GetTransform().GetPosition()
							destroy_enemy(plus, scn, enemy[0])
							enemy_list.remove(enemy)
							scn.RemoveNode(col_pair.GetNodeB())
							debris_list.extend(create_explosion(plus, scn, pos))

							score += 10

				# Game difficulty
				enemy_spawn_interval = max(1.0, enemy_spawn_interval - hg.time_to_sec_f(dt) * 0.025)

				# Cleanup debris
				if len(debris_list) > max_debris:
					tmp_debris = debris_list[0]
					debris_list.remove(debris_list[0])
					tmp_debris.RemoveComponent(tmp_debris.GetRigidBody())
					# scn.RemoveNode(tmp_debris)

			render_aim_cursor(plus, scn, target_angle)
			display_hud(plus, player_life / max_player_life, max(0, turret_cool_down) / turret_cool_down_duration, score)

		# Game over screen
		elif game_state == "GAME_OVER":
			display_game_over(plus, scn, score)
			if plus.KeyReleased(hg.KeySpace):
				game_state = "SCENE_RESET"

		# Reset the playfield for a new game
		elif game_state == "SCENE_RESET":
			for enemy in enemy_list:
				destroy_enemy(plus, scn, enemy[0])

			for debris in debris_list:
				debris.RemoveComponent(debris.GetRigidBody())

			game_state = "GAME_INIT"

		plus.UpdateScene(scn, dt)
		plus.Flip()
		plus.EndFrame()

	return plus

plus = game()
plus.RenderUninit()
