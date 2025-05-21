# Build measure groups first
for i in range(1, 18):
    globals()[f"measure{i}_list"] = [f"measure{i}.{j+1}" for j in range(4)]

measure_groups = [globals()[f"measure{i}_list"] for i in range(1, 18)]
num_groups = len(measure_groups)

# Map slider value (0 to 1) to an integer group index
slider_value = 0.5
group_index = int(slider_value * (num_groups - 1))

# Initialize current measure group and measure index
if current_measure is None:
    current_group_index = 0
    measure_index = 0
else:
    # if current_measure was a string, you’ll need to parse it to find current_group_index and measure_index
    # but for now assume indices:
    current_group_index = 0
    measure_index = 0

goal_group_index = group_index

# Loop through groups towards goal_group_index
while current_group_index != goal_group_index:
    current_group = measure_groups[current_group_index]
    current_measure = current_group[measure_index]
    print(f"Playing {current_measure}")

    # Advance measure index within current group
    measure_index = (measure_index + 1) % len(current_group)
    
    # If wrapped around measures in the group, move to next group step
    if measure_index == 0:
        if current_group_index < goal_group_index:
            current_group_index += 1
        else:
            current_group_index -= 1

# Print final measure at goal group and current measure index
final_group = measure_groups[goal_group_index]
final_measure = final_group[measure_index]

