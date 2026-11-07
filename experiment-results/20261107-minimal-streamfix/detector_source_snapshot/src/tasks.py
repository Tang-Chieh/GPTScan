import yaml
import os
import logging
from typing import Dict, List, Tuple
import config as global_config
import datetime
import json
import falcon_adapter
import traceback
import static_check
import utils
import sys
import time
import argparse
import subprocess
import rich
from rich.progress import Progress
from rich.table import Table
from rich_utils import *
import falcon

logger = logging.getLogger(__name__)

console = rich.get_console()

def _do_load_config(config_path: str):
    with open(os.path.join("tasks", config_path), "r") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    return config


def load_config(config_name: str):
    if os.path.exists(os.path.join("tasks", config_name+".yml")):
        path = os.path.join("tasks", config_name+".yml")
    elif os.path.exists(os.path.join("tasks", config_name+".yaml")):
        path = os.path.join("tasks", config_name+".yaml")
    else:
        raise FileNotFoundError("No such file: {}".format(config_name))
    return _do_load_config(os.path.basename(path))


def load_configs(config_names: list):
    configs = []
    for config_name in config_names:
        configs.append(load_config(config_name))
    return configs


def load_all_configs():
    configs = []
    for file in os.listdir("tasks"):
        if file.endswith(".yml") or file.endswith(".yaml"):
            configs.append(_do_load_config(file))
    return configs


def load_rule(rule_indexs: List[int]):
    result = []
    for rule in rule_indexs:
        if os.path.exists(os.path.join("rules", rule+".yml")):
            result.append(yaml.load(
                open(os.path.join("rules", rule+".yml"), "r"), Loader=yaml.FullLoader))
        else:
            raise FileNotFoundError("No such file: {}".format(rule))
    return result


def load_all_rules():
    from profiles import rule_paths
    result = []
    for path in rule_paths("rules", os.environ.get("GPTSCAN_PROFILE", "price")):
        result.append(yaml.safe_load(path.read_text()))
    return result


def compile_project(abs_path:str):
    # with Progress(transient=True) as progress:
    #     task = progress.add_task("Compiling", total=None, start=False)
    #     data = {
    #         "version": "0.0.1",
    #         "user": {
    #             "project": {
    #                 "workspace": f"{abs_path}"
    #             },
    #             "operation": ["detection", "dependency", "compile"],
    #             "output_format": ["standard", "compatible-ast"],
    #             "output_path": f"{os.path.join(abs_path, 'ast')}"
    #         }
    #     }
    #     json.dump(data, open(os.path.join(abs_path, 'parse-config.json'), "w"))
    #     output = subprocess.check_output(['mt-parsing', 'parse-config.json'], cwd=os.path.abspath(abs_path))
    #     if len(os.listdir(os.path.join(abs_path, "ast", "standard"))) > 0:
    #         return True
    #     else:
    #         logger.error(output)
    #         return False
    if os.path.isfile(abs_path):
        return falcon.Falcon(abs_path)
    files = os.listdir(abs_path)
    files = list(filter(lambda x: x.endswith(".sol") and os.path.isfile(os.path.join(abs_path,x)), files))
    if len(files) == 1:
        return falcon.Falcon(os.path.join(abs_path, files[0]))
    return falcon.Falcon(abs_path)


def simple_cli():
    start_time = time.time()

    parser = argparse.ArgumentParser(
                    prog='GPTScan',
                    description='GPTScan is an AI based smart contract vulnerability scanner.')
    parser.add_argument("-s", "--source", help="The source code directory", required=True)
    # not need ast, compile first
    # parser.add_argument("-a", "--ast", help="The AST directory", required=True)
    parser.add_argument("-o", "--output", help="Primary output: Judge-ready PredictionCase JSON", required=True)
    parser.add_argument("-k", "--gptkey", help="Legacy API key; prefer OPENAI_API_KEY in explicit API mode")
    parser.add_argument("--provider", choices=("codex-gateway", "api"), default="codex-gateway")
    parser.add_argument("--profile", choices=("price", "general"), default="price")
    parser.add_argument("--model", default="openai-codex/gpt-5.6-luna")
    parser.add_argument("--gateway-url", default="http://127.0.0.1:4000/v1")
    parser.add_argument("--gateway-token-file")
    parser.add_argument("--repo-id", required=True, help="Repository identity for the canonical Judge output")
    parser.add_argument("--repo-root", help="Original repository root for relative source locations")
    parser.add_argument("--prediction-output", help="Compatibility alias: optional duplicate of the primary PredictionCase output")
    parser.add_argument("--native-output", help="Optional debug-only native GPTScan results JSON; never a Judge input")
    parser.add_argument("--strict", action="store_true", help="Fail on compilation failure; candidate-level analysis exceptions retain upstream handling")
    parser.add_argument("--archive", help="Verified, path-rebased Crytic Compile archive; never recompile")
    parser.add_argument("--scope-file", help="Shared compiled target inventory from reusable adapter")
    options = parser.parse_args()
    output_paths = {os.path.realpath(options.output), os.path.realpath(options.output + ".metadata.json")}
    if options.prediction_output:
        output_paths.add(os.path.realpath(options.prediction_output))
    if options.native_output and os.path.realpath(options.native_output) in output_paths:
        parser.error("--native-output must not overwrite the PredictionCase or its metadata")
    if options.prediction_output and os.path.realpath(options.prediction_output) == os.path.realpath(options.output + ".metadata.json"):
        parser.error("--prediction-output must not overwrite metadata")
    if bool(options.archive) != bool(options.scope_file):
        parser.error("--archive and --scope-file must be provided together")
    if options.scope_file:
        from reusable_archive import validate_scope, sha256
        scope = json.load(open(options.scope_file))
        validate_scope(scope, options.source)
        if scope.get("archive_sha256") != sha256(options.archive):
            parser.error("Archive and scope hash do not match")
        os.environ["GPTSCAN_SCOPE_FILE"] = os.path.abspath(options.scope_file)
    from model_transport import gateway_url, record_event
    if options.gptkey and options.provider != "api":
        parser.error("-k is only allowed with --provider api; never use it for OAuth")
    if options.provider == "codex-gateway":
        gateway_url(options.gateway_url)
        if not options.gateway_token_file or not os.path.isfile(options.gateway_token_file):
            parser.error("Provide --gateway-token-file for the authorized local gateway")
    if options.prediction_output and not options.repo_id:
        parser.error("--prediction-output requires --repo-id")
    os.environ.update(GPTSCAN_PROVIDER=options.provider, GPTSCAN_MODEL=options.model,
                      GPTSCAN_PROFILE=options.profile, GPTSCAN_BASE_URL=options.gateway_url)
    if options.gateway_token_file:
        os.environ["GPTSCAN_GATEWAY_TOKEN_FILE"] = os.path.abspath(options.gateway_token_file)
    if options.gptkey:
        os.environ["OPENAI_API_KEY"] = options.gptkey
    class ErrorTracker(logging.Handler):
        count = 0
        def emit(self, record):
            if record.levelno >= logging.ERROR:
                self.count += 1
                record_event("analysis_error", error="analysis_error", component=record.name)
    tracker = ErrorTracker()
    logging.getLogger().addHandler(tracker)
    
    
    scan_rules = load_all_rules()
    console.log(f"Loaded [bold green]{len(scan_rules)}[/bold green] rules")
    
    source_dir = os.path.abspath(options.source)

    try:
        if options.archive:
            from reusable_archive import load_falcon
            falcon_instance = load_falcon(options.archive)
        else:
            falcon_instance = compile_project(source_dir)
    except:
        console.log(traceback.format_exc())
        console.log("Compile [bold red]failed[/bold red].")
        console.log("[yellow]Since the compilation is failed, some static analysis tool may not be enabled, which may cause lower precision and recall.[/yellow]")
        falcon_instance = None
        record_event("failed", error="compile_failed")
        if options.strict:
            raise RuntimeError("Compilation failed; no clean-result PredictionCase exported")
    output_file = options.output

    import analyze_pipeline
    import chatgpt_api

    res, cg, meta_data = analyze_pipeline.ask_whether_has_vul_with_scenario_v9(
        source_dir, scan_rules)
    final_result = {}
    # logger.info(res)
    for file in res:
        with open(file) as f:
            source = f.read().splitlines()
            for contract in res[file]:
                for function1 in res[file][contract]:
                    
                    # I think should first ask for function 1
                    # this is a key value map for vul -> result
                    function1_tmp_result = {}

                    for function2 in res[file][contract][function1]:
                        confirmed_vuls = {}
                        for vul in res[file][contract][function1][function2]["data"]:
                            meta_data["rules_types_for_static"].add(vul["name"])
                            # if the rule need static check
                            if "static" in vul:
                                # if need static check

                                # if function1 is not asked yet, ask for function1 first
                                if vul["name"] not in function1_tmp_result:
                                    function1_detail = cg.get_function_detail(file, contract, function1)
                                    function1_text = "\n".join(open(file).read().splitlines()[int(function1_detail['loc']['start'].split(":")[0])-1:int(function1_detail['loc']['end'].split(":")[0])])
                                    try:
                                        args = []
                                        checker = vul["static"]["rule"]["name"]
                                        if "multisteps" in vul["static"] and vul["static"]["multisteps"] == True:
                                            answer = analyze_pipeline.ask_for_static_multistep(vul["static"]["prompt"], function1_text, vul["static"]["output_keys"])
                                            if "filter" in vul["static"]:
                                                for filter_variable in vul["static"]["filter"]:
                                                    if filter_variable in answer:
                                                        for var in answer[filter_variable].copy():
                                                            var_remove_flag = True
                                                            for target_feature in vul["static"]["filter"][filter_variable]:
                                                                if target_feature.lower() in var.lower():
                                                                    var_remove_flag = False
                                                                    break
                                                            if var_remove_flag == True:
                                                                answer[filter_variable].remove(var)
                                                                
                                                    else:
                                                        raise Exception("Filter variable not found")
                                        else:
                                            if "format" in vul["static"] and vul["static"]["format"] == "json":
                                                answer, raw = analyze_pipeline.ask_for_static_json(vul["static"]["prompt"], function1_text, vul["static"]["output_keys"])
                                                if "validate_description" in vul["static"]:
                                                    for to_validate_key, to_validate_values in vul["static"]["validate_description"].items():
                                                        validate_flag = True
                                                        if to_validate_key in raw and answer[to_validate_key] in raw[to_validate_key]:
                                                            for v_line in to_validate_values:
                                                                v_line_flag = False
                                                                for v in v_line:
                                                                    if v.lower() in raw[to_validate_key][answer[to_validate_key]].lower():
                                                                        v_line_flag = True
                                                                        break
                                                                validate_flag = validate_flag and v_line_flag
                                                        if validate_flag == False:
                                                            raise Exception("The description of variable did not pass the `validate_description` validation")
                                                if "exclude_variable" in vul["static"]:
                                                    for to_exclude_key, to_exclude_values in vul["static"]["exclude_variable"].items():
                                                        validate_flag = True
                                                        for var in to_exclude_values:
                                                            if var.lower() in answer[to_exclude_key].lower():
                                                                validate_flag = False
                                                                break
                                                        if validate_flag == False:
                                                            raise Exception("The description of variable did not pass the `exclude_variable` validation")
                                            elif "format" in vul["static"] and vul["static"]["format"] == "json_single":
                                                answer = analyze_pipeline.ask_for_static_json_single(vul["static"]["prompt"], function1_text, vul["static"]["output_keys"][0])
                                            elif "format" in vul["static"] and vul["static"]["format"] == "not_need":
                                                pass
                                            else:
                                                answer = analyze_pipeline.ask_for_static(vul["static"]["prompt"], function1_text, vul["static"]["output_keys"])

                                        if "multisteps" not in vul["static"] or vul["static"]["multisteps"] == False:
                                            for arg in vul["static"]["rule"]["args"]:
                                                if "CONSTANT" in arg:
                                                    args.append(arg["CONSTANT"])
                                                else:
                                                    if "format" in vul["static"] and vul["static"]["format"] == "json" or vul["static"]["format"] == "json_single":
                                                        args.append(answer[arg])
                                                    elif "format" in vul["static"] and vul["static"]["format"] == "not_need":
                                                        args = list(map(lambda x: x["constant"], vul["static"]["args"]))
                                                    else:
                                                        args.append(
                                                            answer[arg].split(" ")[0])
                                        else:
                                            for arg in vul["static"]["rule"]["args"]:
                                                if "CONSTANT" in arg:
                                                    args.append(arg["CONSTANT"])
                                                else:
                                                    args.append(answer[arg])

                                        res_1 = static_check.run_static_check(checker, args, function1, falcon_instance, function1_text, contract, file)
                                        function1_tmp_result[vul["name"]] = res_1
                                    except:
                                        logger.error(
                                            "Static analysis failed: Invalid args")
                                        logger.error(f"Current File: {file}, current function: {function1}, current vul: {vul['name']}")
                                        logger.error(traceback.format_exc())
                                        # raise Exception(
                                        #     "Static analysis failed: Invalid args")
                                        function1_tmp_result[vul["name"]] = False


                                # if function1 is asked, use the result directly
                                # and ask for function2
                                res_2 = None
                                if function2 == "__ONLY_FUNCTION__":
                                    res_2 = False
                                else:
                                    try:
                                        args = []
                                        checker = vul["static"]["rule"]["name"]
                                        function2_splitted = function2.split("!!!")
                                        function2_file = function2_splitted[0]
                                        function2_contract = function2_splitted[1]
                                        function2_func = function2_splitted[2]
                                        function2_detail = cg.get_function_detail(function2_file, function2_contract, function2_func)
                                        function2_text = "\n".join(open(function2_file).read().splitlines()[int(function2_detail['loc']['start'].split(":")[0])-1:int(function2_detail['loc']['end'].split(":")[0])])
                                        if "multisteps" in vul["static"] and vul["static"]["multisteps"] == True:
                                            answer = analyze_pipeline.ask_for_static_multistep(vul["static"]["prompt"], function2_text, vul["static"]["output_keys"])
                                        else:
                                            if "format" in vul["static"] and vul["static"]["format"] == "json":
                                                answer, raw = analyze_pipeline.ask_for_static_json(vul["static"]["prompt"], function2_text, vul["static"]["output_keys"])
                                                if "validate_description" in vul["static"]:
                                                    for to_validate_key, to_validate_values in vul["static"]["validate_description"].items():
                                                        validate_flag = True
                                                        if to_validate_key in raw and answer[to_validate_key] in raw[to_validate_key]:
                                                            for v_line in to_validate_values:
                                                                v_line_flag = False
                                                                for v in v_line:
                                                                    if v.lower() in raw[to_validate_key][answer[to_validate_key]].lower():
                                                                        v_line_flag = True
                                                                        break
                                                                validate_flag = validate_flag and v_line_flag
                                                        if validate_flag == False:
                                                            raise Exception("The description of variable did not pass the validation")
                                                if "exclude_variable" in vul["static"]:
                                                    for to_exclude_key, to_exclude_values in vul["static"]["exclude_variable"].items():
                                                        validate_flag = True
                                                        for var in to_exclude_values:
                                                            if var.lower() in answer[to_exclude_key].lower():
                                                                validate_flag = False
                                                                break
                                                        if validate_flag == False:
                                                            raise Exception("The description of variable did not pass the `exclude_variable` validation")
                                            elif "format" in vul["static"] and vul["static"]["format"] == "json_single":
                                                answer = analyze_pipeline.ask_for_static_json_single(vul["static"]["prompt"], function2_text, vul["static"]["output_keys"][0])
                                            elif "format" in vul["static"] and vul["static"]["format"] == "not_need":
                                                pass
                                            else:
                                                answer = analyze_pipeline.ask_for_static(vul["static"]["prompt"], function2_text, vul["static"]["output_keys"])

                                        if "multisteps" not in vul["static"] or vul["static"]["multisteps"] == False:
                                            for arg in vul["static"]["rule"]["args"]:
                                                if "CONSTANT" in arg:
                                                    args.append(arg["CONSTANT"])
                                                else:
                                                    if "format" in vul["static"] and vul["static"]["format"] == "json" or vul["static"]["format"] == "json_single":
                                                        args.append(answer[arg])
                                                    elif "format" in vul["static"] and vul["static"]["format"] == "not_need":
                                                        args = list(map(lambda x: x["constant"], vul["static"]["args"]))
                                                    else:
                                                        args.append(
                                                            answer[arg].split(" ")[0])
                                        else:
                                            for arg in vul["static"]["rule"]["args"]:
                                                if "CONSTANT" in arg:
                                                    args.append(arg["CONSTANT"])
                                                else:
                                                    args.append(answer[arg])
                                        res_2 = static_check.run_static_check(checker, args, function2_func, falcon_instance, function2_text, function2_contract, function2_file)
                                    except:
                                        logger.error(
                                            "Static analysis failed: Invalid args")
                                        logger.error(f"Current File: {file}, current function: {function1}, current vul: {vul['name']}")
                                        logger.error(traceback.format_exc())
                                        res_2 = False
                                

                                # if function1 and function2 are both asked, merge the result
                                confirmed_vuls[vul["name"]]={"StaticAnalysis": function1_tmp_result[vul["name"]] or res_2}

                            else:
                                confirmed_vuls[vul["name"]]={"StaticAnalysis": "Not Needed"}
                        if len(confirmed_vuls)>0:
                            if file not in final_result:
                                final_result[file] = {}
                            if contract not in final_result[file]:
                                final_result[file][contract] = {}
                            if function1 not in final_result[file][contract]:
                                final_result[file][contract][function1] = {}
                            final_result[file][contract][function1][function2] = confirmed_vuls

    num_true = 0
    num_false = 0
    for file_, file_data_ in final_result.items():
        for contract_, contract_data_ in file_data_.items():
            for function1_, function1_data_ in contract_data_.items():
                for function2_, function2_data_ in function1_data_.items():
                    for vul_, vul_data_ in function2_data_.items():
                        if "StaticAnalysis" in vul_data_:
                            if vul_data_["StaticAnalysis"] == False:
                                num_false += 1
                            else:
                                meta_data["files_after_static"].add(file_)
                                meta_data["contracts_after_static"].add(file_+"!!!"+contract_)
                                meta_data["functions_after_static"].add(file_+"!!!"+contract_+"!!!"+function1_)
                                if function2_ != "__ONLY_FUNCTION__":
                                    meta_data["files_after_static"].add(function2_.split("!!!")[0])
                                    meta_data["contracts_after_static"].add(function2_.split("!!!")[0]+"!!!"+function2_.split("!!!")[1])
                                    meta_data["functions_after_static"].add(function2_)
                                meta_data["rules_types_after_static"].add(vul_)
                                num_true += 1

    # json.dump(res, open(output_file, "w"), indent=4)
    output_json = utils.convert_output(final_result, scan_rules, cg, source_dir)

    meta_data["used_time"]= time.time()-start_time  # 花费时间，单位为秒
    meta_data["vul_before_static"] = num_true + num_false   # 静态分析前，第二次交互为yes的数量，可能有重复（A和A+B）
    meta_data["vul_after_static"] = num_true    # 静态分析后，结果不为False的数量（之前有不需要静态分析的，现在没了）
    meta_data["vul_after_merge"] = len(output_json["results"])  # 去重后的结果数量

    meta_data["token_sent"] = chatgpt_api.tokens_sent.value # 发送的Token数量
    meta_data["token_received"] = chatgpt_api.tokens_received.value # 接收的Token数量
    meta_data["token_sent_gpt4"] = chatgpt_api.tokens_sent_gpt4.value # 发送的Token数量
    meta_data["token_received_gpt4"] = chatgpt_api.tokens_received_gpt4.value # 接收的Token数量
    # Legacy counters were not reliable across spawned workers. Do not claim zero
    # tokens or use historical GPT-3.5 prices for a subscription model.
    for key in ("token_sent", "token_received", "token_sent_gpt4", "token_received_gpt4"):
        meta_data[key] = None
    meta_data["estimated_cost"] = None
    meta_data["model"] = options.model
    meta_data["profile"] = options.profile
    meta_data["compile_succeeded"] = falcon_instance is not None
    meta_data["analysis_errors"] = tracker.count
    meta_data["input_mode"] = "reusable-archive" if options.archive else "compile-project"

    for metadata_key, metadata_value in meta_data.copy().items():
        if isinstance(metadata_value, set):
            meta_data[metadata_key] = len(metadata_value)

    # logger.info("============= Summary ===============")
    # logger.info(json.dumps(meta_data))

    summary_table = Table(title="Summary")
    summary_table.add_column("Key")
    summary_table.add_column("Value")
    summary_table.add_row("Files", str(meta_data["files"]))
    summary_table.add_row("Contracts", str(meta_data["contracts"]))
    summary_table.add_row("Functions", str(meta_data["functions"]))
    summary_table.add_row("Lines of Code", str(meta_data["loc"]))
    summary_table.add_row("Used Time", str(meta_data["used_time"]))
    summary_table.add_row("Estimated Cost (USD)", str(meta_data["estimated_cost"]))

    console.print(summary_table)


    from prediction_export import write_json_atomic, write_prediction_output
    meta_data["output_format"] = "PredictionCase"
    write_json_atomic(output_file + ".metadata.json", meta_data)
    if options.native_output:
        write_json_atomic(options.native_output, output_json)
    write_prediction_output(output_json, output_file, options.repo_id,
                            options.repo_root or source_dir, options.model,
                            "gptscan-price-minimal-upstream7-v3" if options.profile == "price" else "gptscan-general-minimal-v3",
                            alias=options.prediction_output)
