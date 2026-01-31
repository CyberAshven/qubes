-- Super Mario World RAM Reader Test
-- Tests that we can read game state from memory

-- SMW RAM Addresses (from smwcentral.net)
local ADDR = {
    -- Player position
    mario_x = 0x7E0094,          -- 2 bytes: Mario's X position
    mario_y = 0x7E0096,          -- 2 bytes: Mario's Y position
    mario_x_speed = 0x7E007B,    -- 1 byte: X speed (signed)
    mario_y_speed = 0x7E007D,    -- 1 byte: Y speed (signed)

    -- Player state
    powerup = 0x7E0019,          -- 0=small, 1=big, 2=cape, 3=fire
    coins = 0x7E0DBF,            -- Coin count
    lives = 0x7E0DBE,            -- Lives remaining

    -- Game state
    player_on_ground = 0x7E13EF, -- 1 if on ground, 0 if in air
}

-- Powerup names lookup
local powerup_names = {[0]="Small", [1]="Big", [2]="Cape", [3]="Fire"}

-- Register a function to run every frame
gui.register(function()
    -- Read player position
    local x = memory.readword(ADDR.mario_x)
    local y = memory.readword(ADDR.mario_y)
    local x_speed = memory.readbytesigned(ADDR.mario_x_speed)
    local y_speed = memory.readbytesigned(ADDR.mario_y_speed)

    -- Read player state
    local powerup = memory.readbyte(ADDR.powerup)
    local coins = memory.readbyte(ADDR.coins)
    local lives = memory.readbyte(ADDR.lives)
    local on_ground = memory.readbyte(ADDR.player_on_ground)

    local powerup_name = powerup_names[powerup] or "Unknown"

    -- Display on screen (white background box for readability)
    gui.box(5, 5, 160, 85, "#000000AA", "#FFFFFFFF")

    gui.text(10, 8, "=== QUBES SMW TEST ===", "#00FF00")
    gui.text(10, 20, string.format("Position: %d, %d", x, y), "#00FFFF")
    gui.text(10, 32, string.format("Speed: %d, %d", x_speed, y_speed), "#00FFFF")
    gui.text(10, 44, string.format("Powerup: %s", powerup_name), "#FFFF00")
    gui.text(10, 56, string.format("Coins: %d  Lives: %d", coins, lives), "#FFFF00")
    gui.text(10, 68, string.format("On Ground: %s", on_ground == 1 and "Yes" or "No"), "#00FF00")
end)

print("SMW Test Script Loaded!")
print("Start playing to see Mario's stats on screen.")
