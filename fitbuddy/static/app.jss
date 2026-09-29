document.addEventListener("DOMContentLoaded", () => {
    const fitnessForm = document.getElementById("fitness-form");

    if (fitnessForm) {
        fitnessForm.addEventListener("submit", () => {
            const button = document.getElementById("generate-button");

            if (!button) {
                return;
            }

            button.disabled = true;

            button.innerHTML = `
                <span>Generating...</span>
                <span class="spinner">◌</span>
            `;
        });
    }


    const deleteButtons =
        document.querySelectorAll(".delete-user");

    deleteButtons.forEach((button) => {
        button.addEventListener("click", async () => {

            const userId =
                button.dataset.userId;

            if (!userId) {
                return;
            }


            const confirmed =
                window.confirm(
                    `Delete user ${userId}? This cannot be undone.`
                );


            if (!confirmed) {
                return;
            }


            try {

                const response =
                    await fetch(
                        `/api/users/${encodeURIComponent(userId)}`,
                        {
                            method: "DELETE"
                        }
                    );


                const data =
                    await response.json();


                if (!response.ok) {
                    throw new Error(
                        data.detail ||
                        "Unable to delete user."
                    );
                }


                window.location.reload();

            } catch (error) {

                window.alert(
                    error.message
                );
            }
        });
    });
});