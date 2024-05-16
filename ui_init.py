import gradio as gr
import configparser, ast
from extras import *


def run():
    with open("PARAMETERS.txt", "r") as f:
        lines = []
        for line in f.readlines():
            if line == "\n": continue
            lines.append(line)
        USE_GRADIO = ast.literal_eval(lines[23].split("=")[1].strip())
    if USE_GRADIO:
        params = read_param(True)
        for i in range(len(params)):
            params[i] = [str(params[i][0]).strip(), str(params[i][1]).strip()]

        api_keys = []
        with open('API_KEYS.txt', 'r') as f:
            for line in f.readlines():
                if line == "\n": continue
                a = line.split("=")
                api_keys.append([str(a[0]).strip(), str(a[1]).strip()])

        config_path = "config.ini"
        config = configparser.ConfigParser()
        if not os.path.exists(config_path):
            config.add_section("Config")
            config.set("Config", "lang", "en")
            with open(config_path, "w") as f:
                config.write(f)
        with open(config_path, "r") as f:
            config.read_string(f.read())

        language = config.get('Config', 'lang')

        def edit_parameters(params):
            edited_params = {}

            for name, value in params:
                edited_value = value
                edited_params[name] = edited_value

            with open("PARAMETERS.txt", "w") as f:
                for name, value in edited_params.items():
                    f.write(f"{str(name).strip()} = {str(value).strip()}\n")
                    f.write("\n")

            return params

        def set_default():
            write_param()
            params = read_param(True)
            for i in range(len(params)):
                params[i] = [str(params[i][0]).strip(), str(params[i][1]).strip()]
            edited_params = {}

            for name, value in params:
                edited_value = value
                edited_params[name] = edited_value

            with open("PARAMETERS.txt", "w") as f:
                for name, value in edited_params.items():
                    f.write(f"{str(name).strip()} = {str(value).strip()}\n")
                    f.write("\n")

            return params

        def apply_options(lang, keys):
            config.set("Config", "lang", lang)
            with open(config_path, "w") as f:
                config.write(f)

            with open("API_KEYS.txt", "w") as f:
                for line in keys:
                    f.write(f"{line[0]}={line[1]}\n")

        with gr.Blocks() as interface:
            gr.Markdown(f"# Bot Configuration")
            interface.title = f"Bot Configuration"
            with gr.Tab("Parameters"):
                gr.Markdown("## Change parameter values")
                with gr.Row():
                    with gr.Column():
                        inputs = gr.List(label="Change", value=params, interactive=True, col_count=2, headers=["Parameter name", "Value"])
                    with gr.Column():
                        outputs = gr.List(label="Current values", value=params, interactive=False, col_count=2, headers=["Parameter name", "Value"])
                with gr.Row():
                    with gr.Column():
                        submit_button = gr.Button(value="Apply", variant="primary")
                        submit_button.click(fn=edit_parameters, inputs=inputs, outputs=outputs)
                        default_button = gr.Button(value="Default")
                        default_button.click(fn=set_default, inputs=None, outputs=outputs)
                    with gr.Column(): pass
            with gr.Tab("Options"):
                gr.Markdown("## Extra configuration")
                with gr.Row():
                    with gr.Column():
                        lang = gr.Dropdown(["en", "es"], value=language, label="Language")
                        inputs = gr.List(label="API Keys", value=api_keys, interactive=True, col_count=2, headers=["API", "Key"])
                    with gr.Column(): pass
                with gr.Row():
                    with gr.Column():
                        submit_button2 = gr.Button(value="Apply", variant="primary")
                        submit_button2.click(fn=apply_options, inputs=[lang, inputs], outputs=None)
                    with gr.Column(): pass


        interface.launch(inbrowser=True)

    else:
        pass


run()