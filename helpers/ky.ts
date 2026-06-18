import ky, { Hooks } from "ky";
import ObsidianGoogleDrive from "main";
import { Notice } from "obsidian";
import { checkConnection } from "./drive";

const getHooks = (t: ObsidianGoogleDrive): Hooks => ({
	beforeRequest: [
		async (request) => {
			if (t.accessToken.token) {
				if (t.accessToken.expiresAt - Date.now() < 60000) {
					await refreshAccessToken(t);
				}
				request.headers.set(
					"Authorization",
					`Bearer ${t.accessToken.token}`
				);
			}
			return request;
		},
	],
	afterResponse: [
		async (request, options, response) => {
			if (!response.ok) {
				new Notice(`Error: ${await response.text()}`);
				return new Response();
			}
			return response;
		},
	],
});

export const getDriveKy = (t: ObsidianGoogleDrive) => {
	return ky.extend({
		prefixUrl: "https://www.googleapis.com",
		hooks: getHooks(t),
		timeout: 120_000,
	});
};

export const refreshAccessToken = async (t: ObsidianGoogleDrive) => {
	try {
		const secretStorage = t.app.secretStorage
        const response = await fetch("https://oauth2.googleapis.com/token", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams({
                client_id: secretStorage.getSecret('client-id'),
                client_secret: secretStorage.getSecret('client-secret'),
                refresh_token: t.settings.refreshToken,
                grant_type: "refresh_token",
            }),
        });

        const data = await response.json();

		t.accessToken = {
			token: data.access_token,
			expiresAt: Date.now() + data.expires_in * 1000,
		};
		return t.accessToken;
	} catch (e: any) {
		if (!(await checkConnection())) {
			return new Notice(
				"Something is wrong with your internet connection, so we could not fetch a new access token! Once you're back online, please restart Obsidian.",
				0
			);
		}
		t.settings.refreshToken = "";
		t.accessToken = {
			token: "",
			expiresAt: 0,
		};

		new Notice(
			"Something is wrong with your refresh token, please restart Obsidian and then reset it.",
			0
		);
		await t.saveSettings();
		return;
	}
};
